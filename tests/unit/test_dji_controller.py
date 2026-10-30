"""Exercises DJIController against a minimal fake bridge server built
straight from DRONE_BRIDGE.md's wire format - standing in for the Android
BridgeServer so the client side (threading/asyncio bridging, message
encoding, ack handling) can be verified without a physical Mini 3.

Runs the fake server on the asyncio flavor of `websockets`, matching
DJIController's own client, since that's what the real Android/Java
counterpart's traffic pattern looks like from the client's perspective.
"""

import asyncio
import json
import threading
import time

import cv2
import numpy as np
import pytest
from websockets.asyncio.server import serve

from app.drone.controller import MovementCommand
from app.drone.dji_controller import DJIController


class FakeBridge:
    def __init__(self):
        self.received = []
        self.reject_takeoff = False
        self._lock = threading.Lock()
        self._ws = None
        self._server = None
        self.port = None

        ready = threading.Event()

        def run_loop():
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._serve(ready))
            finally:
                loop.close()

        self._loop = None
        self._thread = threading.Thread(target=run_loop, name="fake-bridge", daemon=True)
        self._thread.start()

        if not ready.wait(timeout=5.0):
            raise RuntimeError("fake bridge server did not start in time")

    async def _serve(self, ready):
        self._server = await serve(self._handle, "127.0.0.1", 0)
        self.port = next(iter(self._server.sockets)).getsockname()[1]
        ready.set()
        async with self._server:
            await self._server.serve_forever()

    async def _handle(self, ws):
        with self._lock:
            self._ws = ws
        async for raw in ws:
            msg = json.loads(raw)
            with self._lock:
                self.received.append(msg)
            await self._respond(ws, msg)

    async def _respond(self, ws, msg):
        msg_type = msg.get("type")
        if msg_type == "takeoff":
            ok = not self.reject_takeoff
            await ws.send(json.dumps({"type": "ack", "for_type": "takeoff", "ok": ok, "detail": None if ok else "simulated rejection"}))
        elif msg_type in ("land", "flight_command", "heartbeat", "emergency_stop"):
            await ws.send(json.dumps({"type": "ack", "for_type": msg_type, "ok": True, "detail": None}))

    def received_of_type(self, msg_type):
        with self._lock:
            return [m for m in self.received if m.get("type") == msg_type]

    def push_telemetry(self, **fields):
        payload = {
            "type": "telemetry",
            "battery": None,
            "connected": False,
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "heading": None,
            "velocity_x": None,
            "velocity_y": None,
            "velocity_z": None,
            "timestamp_epoch_ms": int(time.time() * 1000),
        }
        payload.update(fields)
        with self._lock:
            ws = self._ws
        asyncio.run_coroutine_threadsafe(ws.send(json.dumps(payload)), self._loop).result(timeout=2.0)

    def push_message(self, payload):
        ## connect() can return before the server side has registered the connection
        _wait_until(lambda: self._ws is not None)
        with self._lock:
            ws = self._ws
        asyncio.run_coroutine_threadsafe(ws.send(json.dumps(payload)), self._loop).result(timeout=2.0)

    def push_video_frame(self, jpeg_bytes):
        with self._lock:
            ws = self._ws
        asyncio.run_coroutine_threadsafe(ws.send(jpeg_bytes), self._loop).result(timeout=2.0)

    def close(self):
        async def _shutdown():
            self._server.close()

        asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=2.0)
        self._thread.join(timeout=2.0)


def _wait_until(predicate, timeout=2.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError("condition not met within timeout")


@pytest.fixture
def bridge():
    b = FakeBridge()
    yield b
    b.close()


@pytest.fixture
def drone(bridge):
    d = DJIController("127.0.0.1", bridge.port)
    d.connect()
    yield d
    d.disconnect()


def test_connect_and_disconnect_toggle_is_connected(bridge):
    drone = DJIController("127.0.0.1", bridge.port)
    assert not drone.is_connected

    drone.connect()
    assert drone.is_connected

    drone.disconnect()
    assert not drone.is_connected


def test_move_sends_normalized_flight_command_matching_wire_format(drone, bridge):
    drone.move(MovementCommand(forward=0.5, right=-0.25, up=0.1, yaw=-0.2))

    _wait_until(lambda: bridge.received_of_type("flight_command"))
    msg = bridge.received_of_type("flight_command")[-1]

    assert msg["forward"] == 0.5
    assert msg["right"] == -0.25
    assert msg["up"] == 0.1
    assert msg["yaw"] == -0.2
    assert isinstance(msg["sent_at_epoch_ms"], int)


def test_move_clamps_out_of_range_command(drone, bridge):
    drone.move(MovementCommand(forward=5.0))

    _wait_until(lambda: bridge.received_of_type("flight_command"))
    assert bridge.received_of_type("flight_command")[-1]["forward"] == 1.0


def test_move_rejects_non_finite_command_without_sending(drone, bridge):
    drone.move(MovementCommand(forward=float("nan")))

    time.sleep(0.2)
    assert bridge.received_of_type("flight_command") == []


def test_takeoff_succeeds_on_positive_ack(drone):
    drone.takeoff()  # should not raise


def test_takeoff_raises_on_rejection(bridge):
    bridge.reject_takeoff = True
    drone = DJIController("127.0.0.1", bridge.port)
    drone.connect()
    try:
        with pytest.raises(RuntimeError):
            drone.takeoff()
    finally:
        drone.disconnect()


def test_land_succeeds_on_positive_ack(drone):
    drone.land()  # should not raise


def test_telemetry_round_trip_preserves_none_vs_zero(drone, bridge):
    bridge.push_telemetry(
        battery=77,
        connected=True,
        altitude=0,
        heading=180.0,
        velocity_x=0,
        velocity_y=1.5,
        velocity_z=0,
        latitude=None,
        longitude=None,
    )

    _wait_until(lambda: drone.get_battery() == 77)
    telemetry = drone.get_telemetry()

    assert telemetry.connected is True
    assert telemetry.altitude == 0
    assert telemetry.latitude is None
    assert telemetry.velocity.y == 1.5


def test_emergency_stop_does_not_block_waiting_for_an_ack(drone):
    start = time.time()
    drone.emergency_stop()
    assert time.time() - start < 0.5


def test_get_video_frame_returns_none_until_a_frame_arrives(drone):
    assert drone.get_video_frame() is None


def test_get_video_frame_decodes_binary_frame_from_bridge(drone, bridge):
    source = np.zeros((4, 4, 3), dtype=np.uint8)
    source[:, :, 1] = 255  # distinguishable from an all-zero decode failure
    ok, encoded = cv2.imencode(".jpg", source)
    assert ok

    bridge.push_video_frame(encoded.tobytes())

    _wait_until(lambda: drone.get_video_frame() is not None)
    frame = drone.get_video_frame()
    assert frame.shape == (4, 4, 3)


def test_get_video_frame_resets_to_none_after_disconnect(bridge):
    drone = DJIController("127.0.0.1", bridge.port)
    drone.connect()
    source = np.zeros((2, 2, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", source)
    assert ok
    bridge.push_video_frame(encoded.tobytes())
    _wait_until(lambda: drone.get_video_frame() is not None)

    drone.disconnect()

    assert drone.get_video_frame() is None


def test_send_message_delivers_other_parts_messages_as_is(drone, bridge):
    drone.send_message({"type": "say", "text": "Chair ahead", "priority": "URGENT", "pan": -0.6, "volume": 0.8})

    _wait_until(lambda: bridge.received_of_type("say"))
    assert bridge.received_of_type("say")[0] == {"type": "say", "text": "Chair ahead", "priority": "URGENT", "pan": -0.6, "volume": 0.8}


def test_send_message_needs_a_type_and_a_connection(bridge):
    d = DJIController("127.0.0.1", bridge.port)
    with pytest.raises(ConnectionError):
        d.send_message({"type": "say", "text": "x"})
    d.connect()
    try:
        with pytest.raises(ValueError):
            d.send_message({"text": "no type"})
    finally:
        d.disconnect()


def test_message_handler_receives_its_message_type_only(bridge):
    received = []
    d = DJIController("127.0.0.1", bridge.port)
    d.add_message_handler("voice_command", received.append)
    d.connect()
    try:
        bridge.push_message({"type": "voice_command", "command": "WHERE_IS", "argument": "cup"})
        bridge.push_telemetry(battery=80, connected=True)
        _wait_until(lambda: received and d.get_battery() == 80)
        assert received == [{"type": "voice_command", "command": "WHERE_IS", "argument": "cup"}]
    finally:
        d.disconnect()


def test_a_failing_handler_does_not_stop_the_bridge(bridge):
    def broken(msg):
        raise RuntimeError("boom")

    d = DJIController("127.0.0.1", bridge.port)
    d.add_message_handler("voice_command", broken)
    d.connect()
    try:
        bridge.push_message({"type": "voice_command", "command": "REPEAT"})
        bridge.push_telemetry(battery=55, connected=True)
        _wait_until(lambda: d.get_battery() == 55)
    finally:
        d.disconnect()


def test_audio_round_trip_over_the_bridge(bridge):
    """The phone's voice_command reaches MicInput, and AudioOutput's answer goes back
    to the phone as a say message, all through the real DJIController socket."""
    from app.audio_output import AudioOutput, BridgeSpeech, Priority
    from app.mic_input import MicInput
    from app.voice_commands import CommandType

    d = DJIController("127.0.0.1", bridge.port)
    mic = MicInput(d)
    audio = AudioOutput(backend=BridgeSpeech(d.send_message))
    d.connect()
    try:
        mic.start()
        bridge.push_message({"type": "voice_command", "command": "WHERE_IS", "argument": "cup", "confidence": 0.9})
        commands = []
        _wait_until(lambda: commands.extend(mic.poll()) or commands)
        assert commands[0].type == CommandType.WHERE_IS and commands[0].argument == "cup"

        audio.say("Cup on your left", Priority.URGENT, pan=-0.7)
        _wait_until(lambda: bridge.received_of_type("say"))
        assert bridge.received_of_type("say")[0] == {
            "type": "say", "text": "Cup on your left", "priority": "URGENT", "pan": -0.7, "volume": 1.0,
        }
    finally:
        audio.close()
        d.disconnect()
