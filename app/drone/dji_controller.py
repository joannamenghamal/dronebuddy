import asyncio
import json
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np
import websockets

from app.drone.controller import DroneController, MovementCommand, Telemetry, Velocity

logger = logging.getLogger("dronebuddy.drone.dji")

HEARTBEAT_INTERVAL_S = 0.5
CONNECT_TIMEOUT_S = 10.0
ACK_TIMEOUT_S = 5.0


class DJIController(DroneController):
    """Python-side client for the DJI Mini 3 Android bridge.

    The DJI Mobile SDK is Android/iOS-only, so this class cannot fly a Mini 3
    directly — it is a WebSocket client to a separate Android app (see
    android-bridge/) that holds the actual DJI SDK session. See
    DRONE_BRIDGE.md for the wire protocol this implements against.

    `app/main.py`'s control loop is synchronous, so the WebSocket connection
    runs on a dedicated background thread with its own asyncio event loop;
    all public methods here are plain blocking calls that hand work to that
    loop via `asyncio.run_coroutine_threadsafe` and are safe to call from the
    main thread.

    Video arrives as raw binary WebSocket frames (JPEG bytes, no JSON
    envelope) interleaved with the JSON control/telemetry traffic on the same
    socket — `websockets` hands back `bytes` for a binary frame and `str` for
    a text frame, so `_receive_loop` branches on that instead of trying
    `json.loads` on every message. See DRONE_BRIDGE.md.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ws = None
        self._main_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._connected = False
        self._telemetry = Telemetry()
        self._pending_acks: dict = {}
        self._latest_frame: Optional[np.ndarray] = None

    def connect(self) -> None:
        if self._thread is not None:
            return

        ready = threading.Event()
        error_box: list = []

        def run_loop():
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            try:
                self._main_task = loop.create_task(self._main(ready, error_box))
                loop.run_until_complete(self._main_task)
            except asyncio.CancelledError:
                pass
            finally:
                loop.close()

        self._thread = threading.Thread(target=run_loop, name="dji-bridge-ws", daemon=True)
        self._thread.start()

        if not ready.wait(timeout=CONNECT_TIMEOUT_S):
            raise ConnectionError(f"timed out connecting to DJI bridge at {self.host}:{self.port}")
        if error_box:
            raise error_box[0]

    async def _main(self, ready: threading.Event, error_box: list) -> None:
        uri = f"ws://{self.host}:{self.port}"
        try:
            async with websockets.connect(uri, open_timeout=CONNECT_TIMEOUT_S) as ws:
                self._ws = ws
                with self._lock:
                    self._connected = True
                ready.set()
                heartbeat_task = asyncio.ensure_future(self._heartbeat_loop(ws))
                try:
                    await self._receive_loop(ws)
                finally:
                    heartbeat_task.cancel()
        except Exception as exc:
            error_box.append(exc)
            ready.set()
        finally:
            with self._lock:
                self._connected = False
            self._ws = None

    async def _heartbeat_loop(self, ws) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            try:
                await ws.send(json.dumps({"type": "heartbeat", "timestamp": time.time()}))
            except websockets.ConnectionClosed:
                return

    async def _receive_loop(self, ws) -> None:
        async for raw in ws:
            if isinstance(raw, bytes):
                self._handle_video_frame(raw)
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("malformed JSON from bridge, ignoring")
                continue
            self._handle_message(msg)

    def _handle_video_frame(self, jpeg_bytes: bytes) -> None:
        frame = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("failed to decode video frame from bridge, ignoring")
            return
        with self._lock:
            self._latest_frame = frame

    def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "telemetry":
            self._update_telemetry(msg)
        elif msg_type == "ack":
            self._resolve_ack(msg)
        else:
            logger.debug("unhandled bridge message type=%r", msg_type)

    def _update_telemetry(self, msg: dict) -> None:
        with self._lock:
            self._telemetry = Telemetry(
                battery=msg.get("battery"),
                connected=bool(msg.get("connected", False)),
                latitude=msg.get("latitude"),
                longitude=msg.get("longitude"),
                altitude=msg.get("altitude"),
                heading=msg.get("heading"),
                velocity=Velocity(
                    x=msg.get("velocity_x") or 0.0,
                    y=msg.get("velocity_y") or 0.0,
                    z=msg.get("velocity_z") or 0.0,
                ),
                timestamp=(msg.get("timestamp_epoch_ms") or 0) / 1000.0,
            )

    def _resolve_ack(self, msg: dict) -> None:
        # Runs on the event-loop thread, same as the code that registers
        # pending acks below, so no lock is needed for this dict.
        future = self._pending_acks.pop(msg.get("for_type"), None)
        if future is not None and not future.done():
            future.set_result(msg)

    def _send(self, payload: dict) -> None:
        if self._loop is None or self._ws is None:
            raise ConnectionError("not connected to DJI bridge")
        future = asyncio.run_coroutine_threadsafe(self._ws.send(json.dumps(payload)), self._loop)
        future.add_done_callback(self._log_send_error)

    @staticmethod
    def _log_send_error(future) -> None:
        exc = future.exception()
        if exc is not None:
            logger.warning("failed to send message to DJI bridge: %s", exc)

    def _send_and_await_ack(self, payload: dict, timeout: float = ACK_TIMEOUT_S) -> dict:
        if self._loop is None or self._ws is None:
            raise ConnectionError("not connected to DJI bridge")
        future = asyncio.run_coroutine_threadsafe(self._register_and_send(payload, timeout), self._loop)
        try:
            return future.result(timeout=timeout + 1.0)
        except TimeoutError:
            raise TimeoutError(f"no ack for {payload['type']!r} within {timeout}s") from None

    async def _register_and_send(self, payload: dict, timeout: float) -> dict:
        msg_type = payload["type"]
        ack_future = self._loop.create_future()
        self._pending_acks[msg_type] = ack_future
        try:
            await self._ws.send(json.dumps(payload))
            return await asyncio.wait_for(ack_future, timeout=timeout)
        finally:
            self._pending_acks.pop(msg_type, None)

    def disconnect(self) -> None:
        if self._loop is None or self._thread is None:
            return

        # Cancelling _main_task (rather than calling ws.close() directly from
        # this thread) lets the single `async with websockets.connect(...)`
        # block in _main be the only code path that ever closes the socket.
        # Closing it a second time from here raced with that block's own
        # close-on-exit and could hang indefinitely waiting on a waiter the
        # other close() had already resolved.
        if self._main_task is not None:
            self._loop.call_soon_threadsafe(self._main_task.cancel)

        self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._main_task = None
        with self._lock:
            self._connected = False
            self._latest_frame = None

    def takeoff(self) -> None:
        ack = self._send_and_await_ack({"type": "takeoff"})
        if not ack.get("ok"):
            raise RuntimeError(f"takeoff rejected by DJI bridge: {ack.get('detail')}")

    def land(self) -> None:
        ack = self._send_and_await_ack({"type": "land"})
        if not ack.get("ok"):
            raise RuntimeError(f"land rejected by DJI bridge: {ack.get('detail')}")

    def emergency_stop(self) -> None:
        # Fire-and-forget: per DroneController.emergency_stop's contract this
        # must not depend on anything that could itself be in a failed
        # state, including waiting on an ack from the same channel it's
        # trying to interrupt.
        self._send({"type": "emergency_stop", "timestamp": time.time()})

    def move(self, command: MovementCommand) -> None:
        # Must check validity before clamping: clamped() uses min/max, which
        # silently turn NaN into a finite boundary value (e.g. min(1.0, nan)
        # == 1.0) rather than preserving it, so a post-clamp check would miss it.
        if not command.is_valid:
            logger.warning("rejecting non-finite movement command: %s", command)
            return
        clamped = command.clamped()
        self._send(
            {
                "type": "flight_command",
                "forward": clamped.forward,
                "right": clamped.right,
                "up": clamped.up,
                "yaw": clamped.yaw,
                "sent_at_epoch_ms": int(time.time() * 1000),
            }
        )

    def get_battery(self) -> Optional[int]:
        with self._lock:
            return self._telemetry.battery

    def get_telemetry(self) -> Telemetry:
        with self._lock:
            return self._telemetry

    def get_video_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest_frame

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._connected
