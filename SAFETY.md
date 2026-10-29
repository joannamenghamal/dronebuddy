# Safety

This is an autonomous flight system. `app/safety/safety_manager.py` is the
single authority for whether a desired movement command is actually safe to
send — `app/main.py` never calls `drone.move()` with a follow-controller
output directly; every command passes through
`SafetyManager.decide()` first.

## What's implemented

| Condition | Detection | Response |
|---|---|---|
| Emergency stop | `trigger_emergency_stop()` called explicitly (SPACE in `app/main.py`) | Latches; every `decide()` call returns `EMERGENCY_STOP` until `reset_emergency_stop()` is called explicitly. Never clears itself. On DJI this forces a hover; it does not cut the motors. |
| Low battery | Latest telemetry `battery <= MIN_BATTERY_PERCENT` (default 20) | `LAND` |
| Connection / telemetry loss | No telemetry received within `CONNECTION_LOSS_TIMEOUT_S` (default 3.0s) — includes the case where no telemetry has ever arrived | `HOVER` |
| Stale AI command | No command issued within `STALE_COMMAND_TIMEOUT_S` (default 1.0s) | `HOVER` |
| Lost person | No `note_person_visible(True)` within `LOST_PERSON_TIMEOUT_S` (default 2.0s) | `HOVER` |
| Lost person, longer | No `note_person_visible(True)` within `LOST_PERSON_LAND_TIMEOUT_S` (default 5.0s) | `LAND` |
| Invalid command | `MovementCommand` contains `NaN`/`Infinity` on any axis | Rejected, `HOVER` |
| Command output limits | Any axis outside `[-1.0, 1.0]` | Clamped in `MovementCommand.clamped()` before being sent |

Priority order (highest first): emergency stop > low battery > (connection
loss / stale command -> hover) > lost person (land after 5s, hover before
that) > invalid command > nominal execute.

Once `app/main.py` has asked the drone to land (low battery or lost person),
it sends nothing else for the rest of the session except an emergency stop,
so the user walking back into view doesn't interrupt the landing. See `SafetyManager.decide()` for the exact order.

## What connection loss can and can't do

If the radio link to the aircraft is actually gone, nothing sent from this
process reaches it — `SafetyManager` returning `HOVER` in that case is
best-effort for a *brief* telemetry gap, not a guarantee. The real mitigation
for true link loss is the aircraft's own firmware failsafe: DJI aircraft
support configurable return-to-home-on-signal-loss (the archived Tello
backend's aircraft had its own equivalent — hover then auto-land — for
reference). **This project must never disable, bypass, or second-guess those
firmware failsafes.** Nothing in `SafetyManager` or any `DroneController`
implementation should touch DJI geofencing or firmware safety settings.

## What's explicitly not implemented yet

- **Manual-control override.** There is currently no RC/manual input path in
  this codebase at all — the only active `DroneController` implementations
  (`mock`, and `dji` once built) only ever receive commands from this
  autonomy loop. Before any real flight with a person nearby, there should
  be a way for a human with a physical remote to take priority over the
  autonomous commands. This needs to be resolved before `--drone dji`
  autonomous flight, not before ground testing with `--drone mock`.
- **SDK-level error handling for a DJI bridge** — there is no DJI
  implementation yet (see [DRONE_BRIDGE.md](DRONE_BRIDGE.md)), so SDK error
  handling is speculative until that exists.
- **Video-loss handling.** Today, `main.py` treats a `None` frame from
  `get_video_frame()` as a reason to stop the loop entirely (see `app/main.py`).
  That's correct for `mock` (a `None` frame there usually means the stream
  died), but it hasn't been evaluated against how a DJI bridge would surface
  a dropped video frame over the WebSocket link — that's an open question
  for `DJIController`, not yet answered.

## Config knobs affecting safety (`app/config.py` / `.env.example`)

`MIN_BATTERY_PERCENT`, `STALE_COMMAND_TIMEOUT_S`, `CONNECTION_LOSS_TIMEOUT_S`,
`LOST_PERSON_TIMEOUT_S`, `LOST_PERSON_LAND_TIMEOUT_S`, `MAX_FORWARD_SPEED`, `MAX_LATERAL_SPEED`,
`MAX_VERTICAL_SPEED`, `MAX_YAW_RATE`. Defaults are intentionally conservative
(speeds at 20-30% of platform max). Raise them only after verifying behavior
with `--drone mock`, then with `--drone dji` on the ground, per
[TESTING.md](TESTING.md).

## Logging

Safety-relevant events (any non-`NOMINAL` state, emergency stop) are logged
at `WARNING`/`INFO` under the `dronebuddy.safety` logger name — see
`app/logging_setup.py`. Never log credentials or bridge auth tokens; none
exist yet, but this applies the moment `DRONE_BRIDGE.md`'s open
authentication question is resolved.
