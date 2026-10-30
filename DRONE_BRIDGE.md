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
Python AI / Autonomy  <--WebSocket-->  Android app [BridgeServer | DJI layer]  <--DJI Mobile SDK-->  DJI Mini 3
```

Inside the Android app the two halves are kept apart. `BridgeServer` only
carries messages: it decodes and validates what Python sends, hands it to
the app through `BridgeServer.Handler`, and sends acks, telemetry and video
back. It never calls the DJI SDK. The app (`MainActivity` and the `dji/`
classes) owns the DJI connection: SDK registration, virtual stick,
takeoff/land, telemetry, the camera feed, and what each command means for
the aircraft. `DjiCommandHandler` is the app's `BridgeServer.Handler`.

## Transport

WebSocket, one connection, Android app as the server (`BridgeServer.kt`),
Python process as the client (`DJIController`). Swapping what's behind
`BridgeServer.Handler` changes nothing on the wire. Chosen over raw TCP/UDP for
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

`BridgeServer` hands this straight to `Handler.onEmergencyStop()` and acks
it. `DjiCommandHandler` forces an immediate hover via
`VirtualStickManager`. This is `land()`'s
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

### `voice_command` (Android -> Python)

```json
{"type": "voice_command", "command": "WHERE_IS", "argument": "cup", "heard": "where is my mug", "confidence": 0.82}
```

The visually impaired user's spoken command, recognized on the phone while
its full-screen push-to-talk button is held. `command` is one of
`START_SESSION`, `STOP_SESSION`, `WHERE_IS`, `REPEAT`, `LOUDER`, `QUIETER`
(`app/voice_commands.py`); `argument` is a YOLO class name for `WHERE_IS`
(the app maps "mug" to `cup`), else `null`; `heard` is the raw speech-to-text
for the session log. No ack. Python side: `MicInput` (registered with
`DJIController.add_message_handler`) ignores unknown commands and anything
below 0.5 `confidence`.

### `say` (Python -> Android)

```json
{"type": "say", "text": "Chair ahead", "priority": "URGENT", "pan": -0.6, "volume": 0.8}
```

Something to speak to the user with the phone's text-to-speech. `priority`
is `NORMAL` or `URGENT`; an `URGENT` one cuts off a `NORMAL` one already
playing. `pan` is -1.0 (left ear) .. +1.0 (right ear); `volume` is 0.0 ..
1.0. No ack: a missed sentence is replaced by the next alert. Python side:
`BridgeSpeech`, sent with `DJIController.send_message`. Both audio messages
are built and parsed in `app/bridge_messages.py`.

### Video (Android -> Python)

Raw binary WebSocket frames — JPEG bytes, no JSON envelope — interleaved on
the same socket as the JSON control/telemetry traffic above. `websockets`
on the Python side hands back `bytes` for a binary frame and `str` for a
text frame, so `DJIController._receive_loop` branches on that instead of
`json.loads`-ing everything.

Android side: `DjiCameraStreamProvider` registers a
`CameraStreamManager.addFrameListener` callback (MSDK V5's live camera
feed API, `ComponentIndexType.LEFT_OR_MAIN`, `FrameFormat.RGBA_8888`),
throttles to one frame per `minIntervalMs` (default 100ms / 10fps — the
raw feed can push far faster than the follow-me loop consumes frames or
the link can carry comfortably), JPEG-encodes via `Bitmap.compress`, and
hands the bytes to `BridgeServer.sendVideoFrame` (wired up in `MainActivity`).
`MainActivity` starts it when the aircraft connects (not at app launch,
before the SDK is ready) and stops it on disconnect. The app has no
on-screen video view, so `DjiCameraStreamProvider` turns on
`CameraStreamManager.setKeepAliveDecoding(true)`: without a render
Surface and with keep-alive off, MSDK doesn't decode the stream and frame
listeners never fire.

On the Python side, `app/main.py` waits up to 10s for the first frame
with `--drone dji`, then exits with an error naming the likely cause.
`DJIController.get_video_frame()` returns a copy, so drawing the HUD on it
doesn't stack onto the next call's frame.

Chosen over a separate RTMP/RTSP channel to avoid a second connection
lifecycle and a second place authentication would eventually need adding —
see the open item below. **Still unverified**: realistic frame rate/latency
against a physical Mini 3, and whether `ComponentIndexType.LEFT_OR_MAIN` is
in fact the index the aircraft reports (it's the index DJI's own samples
bind for single-camera aircraft, but this environment has no hardware to
confirm against the base Mini 3 specifically).

## Required behavior on the Android side

Split between the transport (`BridgeServer`) and the app's DJI layer
(`DjiCommandHandler`):

- **Stale-command detection** (`DjiCommandHandler`): while a client is
  connected, if no valid `flight_command` has arrived within
  `staleCommandTimeoutMs` (default 1000ms), its watchdog forces a hover
  rather than continuing the last velocity indefinitely. Heartbeats do not
  count as commands.
- **Connection-loss detection** (`BridgeServer`): if no message (including
  heartbeats) has arrived within `connectionLossTimeoutMs` (default
  3000ms), it calls `Handler.onLinkLost()` once, and `DjiCommandHandler`
  hovers. A silent link also stops delivering commands, so the stale-command
  hover covers it too. Nothing here disables or overrides the DJI
  firmware's own RC-signal-loss failsafe.
- **Command validation** (`BridgeServer`, via `ProtocolCodec`): any
  `flight_command` with a value outside `[-1.0, 1.0]` or non-finite
  (`NaN`/`Infinity`) is rejected with a `false` ack and never handed to
  the app.
- **Safe default** (`DjiCommandHandler`): on client connect, on client
  disconnect, and on socket error, the app forces a hover, never the last
  command received.
- **Takeoff and landing are left alone** (`DjiCommandHandler`): from a
  `takeoff`/`land` until the next `flight_command` or `emergency_stop`, none
  of the hovers above are sent. `app/main.py` stops sending commands after
  asking to land, and hover inputs during DJI's auto-landing or takeoff
  could cancel it.
- **Audio**: `BridgeServer` hands each valid `say` to its `onSay` callback;
  `MainActivity` passes them to `SpeechPlayer`, which speaks them with
  Android text-to-speech, cutting off a `NORMAL` sentence for an `URGENT`
  one and dropping stale `NORMAL` ones (`SpeechPolicy`). Written but not yet
  run on a device. Still to build: the push-to-talk screen, which must call
  `SpeechPlayer.stopSpeaking()` when pressed and
  `BridgeServer.sendVoiceCommand()` when released. Audio messages never
  affect flight; a failing speech callback is only logged.

Building your own Android app against this protocol? See
[BRIDGE_INTEGRATION.md](BRIDGE_INTEGRATION.md).

## What's still open

- **Emergency stop semantics**: see the `emergency_stop` section above —
  genuinely unverified without a physical aircraft.
- **Authentication**: none. If this bridge ever runs on a network where an
  untrusted device could reach it, it needs one — don't skip this when
  moving past ground testing on a private network.
