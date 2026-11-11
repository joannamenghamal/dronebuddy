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
| Frozen video (DJI) | No new frame from the phone for 1s (`MAX_FRAME_AGE_S` in `dji_controller.py`), once video has started | `main.py` says "Video lost" and ends the session; the phone app then hovers the drone and hands the sticks back to the controller. Without this, the last frame would be reused and the drone would keep following where the user was. At startup `main.py` waits up to 10s for the first frame instead |
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

- **Taking back control is untested on the Mini 3.** The phone app only
  enables virtual stick while the laptop is connected and responsive (see
  [android-app/README.md](android-app/README.md)), so quitting the laptop
  program, or 3s of silence from it, hands the sticks back to the pilot.
  Whether the Mini 3 really ignores the sticks while virtual stick is on, and
  whether the controller's Pause button exits it, still has to be confirmed
  on the aircraft (step 3 of the flight-test procedure in
  [TESTING.md](TESTING.md)).
- **SDK error handling** beyond logging (e.g. what to do if enabling virtual
  stick fails mid-flight) hasn't been tested against real failures.

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
