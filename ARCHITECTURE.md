# Architecture

## Pipeline

```
Camera
   |
OpenCV
   |
YOLO (app/person_detector.py)
   |
Person Detection
   |
Person Tracking (app/person_tracker.py)
   |
Follow-Me Controller (app/control/follow_controller.py)
   |
SafetyManager (app/safety/safety_manager.py)
   |
DroneController (app/drone/controller.py)
   |
MockDroneController | DJIController (not yet implemented)
```

(`TelloController` also implements this interface but is archived — see
below.)

`app/main.py` wires these together. Everything above `SafetyManager` in this
diagram is platform-agnostic: it imports `app.drone.controller` only, never
`djitellopy` or a DJI SDK class directly.

## Why a SafetyManager sits between the controller and the follow-me logic

The follow-me controller only knows about the person it's tracking; it has
no idea whether the link to the aircraft is healthy, whether telemetry is
current, or whether the battery is low. `SafetyManager.decide()` is the one
place that combines a *desired* `MovementCommand` with everything else known
about system health, and returns what should *actually* happen
(`EXECUTE` / `HOVER` / `LAND` / `EMERGENCY_STOP`). See [SAFETY.md](SAFETY.md).

## The drone abstraction

`app/drone/controller.py` defines:

- `DroneController` — the abstract interface (`connect`, `disconnect`,
  `takeoff`, `land`, `emergency_stop`, `move`, `get_battery`,
  `get_telemetry`, `get_video_frame`, `is_connected`).
- `MovementCommand` — `forward`/`right`/`up`/`yaw`, each normalized to
  `[-1.0, 1.0]` as a fraction of *that platform's own* configured max speed.
  Normalizing here (instead of drone-specific units like Tello's `-100..100`
  RC units or DJI's virtual-stick values) is what keeps the follow-me
  controller from needing to know which aircraft it's flying.
- `Telemetry` — battery/connected/lat/lon/altitude/heading/velocity/timestamp.
  Fields a platform can't provide (e.g. GPS on a Tello) are `None`, not `0`,
  so a `None` can't be misread as a valid reading of zero.

Implementations today:

| Class | File | Status |
|---|---|---|
| `MockDroneController` | `app/drone/mock_controller.py` | Working — for running the pipeline with `--drone mock`, and for tests |
| `DJIController` | `app/drone/dji_controller.py` | Not implemented — every method raises `NotImplementedError`. It's a WebSocket client to a separate Android app; see [DRONE_BRIDGE.md](DRONE_BRIDGE.md) and [DJI_MINI_3_SETUP.md](DJI_MINI_3_SETUP.md) |
| `TelloController` | `archive/tello/tello_controller.py` | Archived, not wired into `--drone` — working at the time it was archived; see [archive/tello/README.md](archive/tello/README.md) |

## What changed vs. the pre-migration behavior

The original `app/main.py` computed and *displayed* a follow-me action
(`"MOVE LEFT + FORWARD"`, etc.) but never actually sent a movement command to
the Tello — it was detection/visualization only. The refactored `main.py`
does call `drone.move()`, gated through `SafetyManager`. Conservative
defaults (`MAX_FORWARD_SPEED=0.3`, etc., in `app/config.py`) and a `mock`
default platform mean nothing flies unless you explicitly pass `--drone dji`
(once implemented) with an aircraft actually connected. See
[TESTING.md](TESTING.md) before ever doing that.

## Directory layout

```
app/
  main.py                    # wiring: detection -> tracking -> follow -> safety -> drone
  config.py                  # env-var configuration, conservative defaults
  logging_setup.py           # structured logging config
  person_detector.py         # YOLO wrapper (unchanged, platform-agnostic)
  person_tracker.py          # bbox -> direction/distance (unchanged, platform-agnostic)
  control/
    follow_controller.py     # decision table (unchanged) + get_movement_command adapter (new)
  drone/
    controller.py            # DroneController interface, MovementCommand, Telemetry
    mock_controller.py        # in-memory fake for tests / --drone mock
    dji_controller.py         # NotImplementedError stub - see DRONE_BRIDGE.md
  safety/
    safety_manager.py        # connection-loss / stale-command / lost-person / battery / e-stop
archive/
  tello/                      # archived Tello backend, not wired into --drone - see its README
    tello_controller.py
    camera_test.py
    test_flight.py            # manual, real-hardware script - never auto-run by pytest
tests/
  unit/                       # command conversion, validation, clamping, safety states
  integration/                 # detection(fixture boxes) -> tracking -> follow -> mock drone
```
