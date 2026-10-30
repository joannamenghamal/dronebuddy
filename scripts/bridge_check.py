"""Checks an Android app's bridge server against DRONE_BRIDGE.md without
flying: run it from a laptop on the same Wi-Fi as the phone and it reports
whether acks, telemetry and video come back the way app/drone/dji_controller.py
expects them.

It only ever sends heartbeats, all-zero flight_commands (hover) and one
out-of-range flight_command that the app must reject. It never sends
takeoff, land or emergency_stop.

Usage: python3 -m scripts.bridge_check --host <phone ip> [--port 8765] [--seconds 10] [--save-frame frame.jpg]
"""

import argparse
import asyncio
import json
import sys
import time

import cv2
import numpy as np
import websockets

COMMAND_INTERVAL_S = 0.1
HEARTBEAT_INTERVAL_S = 0.5

TELEMETRY_FIELDS = (
    "battery", "connected", "latitude", "longitude", "altitude", "heading",
    "velocity_x", "velocity_y", "velocity_z", "timestamp_epoch_ms",
)


def hover_command():
    return {"type": "flight_command", "forward": 0.0, "right": 0.0, "up": 0.0, "yaw": 0.0,
            "sent_at_epoch_ms": int(time.time() * 1000)}


class Report:
    def __init__(self):
        self.acks = {}             # for_type -> [ok values]
        self.telemetry = []
        self.bad_telemetry = []    # (missing fields, message)
        self.frames = 0
        self.undecodable_frames = 0
        self.largest_frame_bytes = 0
        self.frame_shape = None
        self.first_frame_at = None
        self.last_frame = None
        self.unknown = []

    def handle(self, raw, started_at):
        if isinstance(raw, bytes):
            self.frames += 1
            self.largest_frame_bytes = max(self.largest_frame_bytes, len(raw))
            frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                self.undecodable_frames += 1
                return
            if self.first_frame_at is None:
                self.first_frame_at = time.monotonic() - started_at
            self.frame_shape = frame.shape
            self.last_frame = frame
            return

        msg = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "ack":
            self.acks.setdefault(msg.get("for_type"), []).append(msg.get("ok"))
        elif msg_type == "telemetry":
            missing = [f for f in TELEMETRY_FIELDS if f not in msg]
            if missing:
                self.bad_telemetry.append((missing, msg))
            self.telemetry.append(msg)
        else:
            self.unknown.append(msg)


async def run(host, port, seconds):
    report = Report()
    async with websockets.connect(f"ws://{host}:{port}", open_timeout=10, max_size=16 * 1024 * 1024) as ws:
        started_at = time.monotonic()

        async def receive():
            async for raw in ws:
                report.handle(raw, started_at)

        async def send():
            await ws.send(json.dumps({**hover_command(), "forward": 5.0}))  # must be rejected
            next_heartbeat = 0.0
            while time.monotonic() - started_at < seconds:
                now = time.monotonic() - started_at
                if now >= next_heartbeat:
                    await ws.send(json.dumps({"type": "heartbeat", "timestamp": time.time()}))
                    next_heartbeat = now + HEARTBEAT_INTERVAL_S
                await ws.send(json.dumps(hover_command()))
                await asyncio.sleep(COMMAND_INTERVAL_S)
            await asyncio.sleep(0.5)  # let the last acks arrive

        receiver = asyncio.create_task(receive())
        await send()
        receiver.cancel()
    return report


def summarize(report, seconds):
    checks = []

    def check(name, passed, detail):
        checks.append(passed)
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    heartbeat_acks = report.acks.get("heartbeat", [])
    check("heartbeat acks", bool(heartbeat_acks) and all(heartbeat_acks),
          f"{len(heartbeat_acks)} received")

    command_acks = report.acks.get("flight_command", [])
    rejected = command_acks.count(False)
    accepted = command_acks.count(True)
    check("hover flight_commands accepted", accepted > 0, f"{accepted} ok acks")
    check("out-of-range flight_command rejected", rejected == 1,
          f"{rejected} rejections (expected exactly 1, for forward=5.0)")

    telemetry_rate = len(report.telemetry) / seconds
    check("telemetry arriving", telemetry_rate >= 1.0, f"{len(report.telemetry)} messages, {telemetry_rate:.1f}/s")
    check("telemetry has every field", not report.bad_telemetry,
          "ok" if not report.bad_telemetry else f"missing {report.bad_telemetry[0][0]}")
    if report.telemetry:
        last = report.telemetry[-1]
        print(f"       last telemetry: battery={last.get('battery')} connected={last.get('connected')} "
              f"altitude={last.get('altitude')} heading={last.get('heading')}")
        check("aircraft connected (per telemetry)", bool(last.get("connected")),
              "app reports the drone connected" if last.get("connected") else "app reports NO drone connected")

    if report.frames:
        fps = report.frames / max(seconds - (report.first_frame_at or 0), 0.001)
        check("video frames arriving", report.undecodable_frames == 0,
              f"{report.frames} frames, ~{fps:.1f} fps, first after {report.first_frame_at:.1f}s, "
              f"{report.frame_shape[1]}x{report.frame_shape[0]}, largest {report.largest_frame_bytes // 1024} KB, "
              f"{report.undecodable_frames} not decodable as JPEG")
    else:
        check("video frames arriving", False, "none received - see BRIDGE_INTEGRATION.md 'No video'")

    if report.unknown:
        print(f"[INFO] {len(report.unknown)} messages of unknown type, first: {report.unknown[0]}")

    return all(checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, help="phone's IP address on the shared Wi-Fi")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--save-frame", help="write the last video frame received to this file")
    args = parser.parse_args()

    try:
        report = asyncio.run(run(args.host, args.port, args.seconds))
    except (OSError, asyncio.TimeoutError, websockets.InvalidHandshake) as exc:
        print(f"[FAIL] connect to ws://{args.host}:{args.port}: {exc}")
        sys.exit(1)

    ok = summarize(report, args.seconds)
    if args.save_frame and report.last_frame is not None:
        cv2.imwrite(args.save_frame, report.last_frame)
        print(f"saved last frame to {args.save_frame}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
