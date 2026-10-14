# Python <-> Android Bridge Protocol

Status: **implemented on both sides.** `app/drone/dji_controller.py` is a real
WebSocket client; `android-bridge/` is a real Android app holding the DJI SDK
session. This document is the ground truth for the wire format both sides
were built against — if you change one side, update this file and the other
side in the same change.

## Why a bridge at all

The DJI Mobile SDK is Android/iOS-only — there is no Python or desktop
binding. A Mini 3 can only be commanded by a mobile app holding an active
DJI SDK registration and RC connection. This repo's autonomy code runs on a
companion computer in Python, so an Android process has to sit in between:

```
Python AI / Autonomy  <--WebSocket-->  Android DJI Bridge  <--DJI Mobile SDK-->  DJI Mini 3
```

## Transport

WebSocket, one connection, Android app as the server (`BridgeServer.kt`),
Python process as the client (`DJIController`). Chosen over raw TCP/UDP for
built-in framing and a ping/pong keepalive; chosen over HTTP polling because
flight commands need low, consistent latency in both directions.

## Messages

All messages are a flat JSON object with a `type` field. Field names below
are exactly what `ProtocolCodec` (Android) and `DJIController` (Python)
produce/consume — this is not aspirational.

### `flight_command` (Python -> Android)

```json
{"type": "flight_command", "forward": 0.0, "right": 0.0, "up": 0.0, "yaw": 0.0, "sent_at_epoch_ms": 0}
```

- `forward`/`right`/`up`/`yaw`: floats in `[-1.0, 1.0]`, matching
  `app.drone.controller.MovementCommand`. `DjiVirtualStickController` scales
  these into real velocity units (m/s, deg/s) using its own conservative
  `MAX_*` constants, clamped again against DJI's `VirtualStickRange`
  ceilings as a hard backstop — Python never sends drone-specific units.
- `sent_at_epoch_ms`: Unix epoch milliseconds (int) when Python generated
  the command, used by Android for stale-command detection (see below).
- Rejected by `ProtocolCodec.decodeFlightCommand` (silently, with a
  `false` ack) if any axis is non-finite or outside `[-1.0, 1.0]`, or if
  `sent_at_epoch_ms` is missing/negative.

### `takeoff` / `land` (Python -> Android)

```json
{"type": "takeoff"}
{"type": "land"}
```

No payload. These are DJIKey action calls (`KeyStartTakeoff` /
`KeyStartAutoLanding` on `DJIFlightControllerKey`, wrapped by
`DjiFlightActions`), not virtual-stick input — a Mini 3 does not leave the
ground just from `sendVirtualStickAdvancedParam`. Both are acknowledged
asynchronously once the SDK action callback fires (see `ack` below);
`DJIController.takeoff()`/`land()` block on that ack (default timeout 5s)
and raise if the bridge reports failure or the ack never arrives.

### `telemetry` (Android -> Python)

```json
{
  "type": "telemetry",
  "battery": 82,
  "connected": true,
  "latitude": 0,
  "longitude": 0,
  "altitude": 0,
  "heading": 0,
  "velocity_x": 0,
  "velocity_y": 0,
  "velocity_z": 0,
  "timestamp_epoch_ms": 0
}
```

Maps onto `app.drone.controller.Telemetry` (velocity fields flatten into its
nested `Velocity`). Fields the SDK can't supply come through as JSON `null`
(decoded to Python `None`), not `0` — `0` is a valid reading and must stay
distinguishable from "unavailable." `connected` reflects DJI SDK aircraft
connection state (`onProductConnect`/`onProductDisconnect`), not the
WebSocket link itself — `DJIController.is_connected` is the latter.

### `heartbeat` (Python -> Android)

```json
{"type": "heartbeat", "timestamp": 0}
```

Sent by `DJIController` every 0.5s, independent of command/telemetry
traffic, so Android's watchdog can tell a silent-but-open socket apart from
a genuinely stalled Python process. Acknowledged like any other message.
Android does not currently send heartbeats back — its own liveness is
carried by `telemetry` pushes and `ack`s.

### `emergency_stop` (Python -> Android)

```json
{"type": "emergency_stop", "timestamp": 0}
```

Android treats this as highest priority: it forces an immediate hover via
`VirtualStickManager`, ahead of anything already queued. This is `land()`'s
and `takeoff()`'s opposite in one respect — `DJIController.emergency_stop()`
does **not** wait for the ack, since blocking on the same channel it's
trying to interrupt would violate `DroneController.emergency_stop`'s "must
not depend on anything that could itself be in a failed state" contract.
**Still unverified**: whether the Mini 3 exposes an SDK-level emergency
stop/motor-cutoff distinct from a virtual-stick hover. Today this bridge
only ever forces a hover — it does not claim to cut power, and the DJI
firmware's own RC-loss/geofence failsafes are never bypassed or overridden.

### `ack` (Android -> Python)

```json
{"type": "ack", "for_type": "flight_command", "ok": true, "detail": null}
```

Sent for every `flight_command`, `heartbeat`, `emergency_stop`, `takeoff`,
and `land`. `ok: false` carries a `detail` string when Android rejects or
fails a command (validation failure, or an `IDJIError` from the SDK for
`takeoff`/`land`).

## Required behavior on the Android side

- **Stale-command detection**: if no valid `flight_command` has arrived
  within `staleCommandTimeoutMs` (default 1000ms), `BridgeServer`'s watchdog
  forces a hover rather than continuing the last velocity indefinitely.
- **Connection-loss detection**: if no message (including heartbeats) has
  arrived within `connectionLossTimeoutMs` (default 3000ms), the watchdog
  forces a hover. This bridge never disables or overrides the DJI
  firmware's own RC-signal-loss failsafe.
- **Command validation**: `ProtocolCodec` rejects any `flight_command` with
  a value outside `[-1.0, 1.0]` or non-finite (`NaN`/`Infinity`) before it
  reaches `DjiVirtualStickController`.
- **Safe default**: on client connect, on client disconnect, and on socket
  error, `BridgeServer` forces a hover — never the last command received.

## What's still open

- **Video**: not implemented. `DJIController.get_video_frame()` returns
  `None` rather than inventing a transport the Android side doesn't speak.
  Whether video should travel over this same WebSocket (base64/binary
  frames) or a separate channel (e.g. RTMP/RTSP from the Android app) is
  still undecided — depends on what frame rate/latency the SDK's camera
  stream API can sustain when re-encoded and pushed off-device.
- **Emergency stop semantics**: see the `emergency_stop` section above —
  genuinely unverified without a physical aircraft.
- **Authentication**: none. If this bridge ever runs on a network where an
  untrusted device could reach it, it needs one — don't skip this when
  moving past ground testing on a private network.
