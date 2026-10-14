# Architecture

## Pipeline

```
Camera / drone.get_video_frame()
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
MockDroneController | DJIController
```

(`TelloController` also implements this interface but is archived — see
below.)

`app/main.py` wires these together. Everything above `SafetyManager` in this
diagram is platform-agnostic: it imports `app.drone.controller` only, never
`djitellopy` or a DJI SDK class directly.

End-to-end, one frame at a time:

1. **Video in → person detection.** `drone.get_video_frame()` supplies the
   frame — on `DJIController`, decoded from JPEG frames the Android bridge
   pushes over the bridge WebSocket (see `DRONE_BRIDGE.md`'s "Video"
   section). YOLO detects objects and draws every bounding box, but only
   `person` detections drive the drone.
2. **Tracking → desired command.** For each detected person,
   `person_tracker.py` computes `direction` (left/right/center, from
   position in frame) and `distance_status` (too close/too far/good, from
   box size). `follow_controller.py` turns that into a human-readable
   `action` label (for the on-screen overlay) and a `desired_command`
   (`MovementCommand`, scaled by the speed limits in `config.py`). No person
   visible → `HOVER`.
3. **Safety override.** `SafetyManager.decide()` combines that desired
   command with telemetry (battery, connection) and person-visibility
   history, and returns what actually happens: `EXECUTE`, `HOVER`, `LAND`,
   or `EMERGENCY_STOP`. This is the only layer that can override "just
   follow the person" — see [SAFETY.md](SAFETY.md).
4. **Drone abstraction.** The resulting action is sent through
   `DroneController` — `MockDroneController` for development/testing with no
   hardware, or `DJIController`, a WebSocket client that talks to the
   Android bridge app (`android-bridge/`), which holds the actual DJI
   Mobile SDK session and talks to the physical Mini 3.
5. **Display.** An OpenCV window shows the live feed with bounding boxes and
   the direction/distance/action overlay; `q` quits.

Run with `python3 -m app.main --drone mock` (no hardware) or `--drone dji`
(real Mini 3, once the bridge app is running and `BRIDGE_HOST` points at
it — see [android-bridge/README.md](android-bridge/README.md)).

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
| `DJIController` | `app/drone/dji_controller.py` | Implemented — a WebSocket client to the Android bridge app (`android-bridge/`), which holds the DJI Mobile SDK session, including video (JPEG frames over the same socket). Takeoff is manual (via the RC) — `app/main.py` never calls `takeoff()` itself. See [DRONE_BRIDGE.md](DRONE_BRIDGE.md) and [DJI_MINI_3_SETUP.md](DJI_MINI_3_SETUP.md) |
| `TelloController` | `archive/tello/tello_controller.py` | Archived, not wired into `--drone` — working at the time it was archived; see [archive/tello/README.md](archive/tello/README.md) |

## What changed vs. the pre-migration behavior

The original `app/main.py` computed and *displayed* a follow-me action
(`"MOVE LEFT + FORWARD"`, etc.) but never actually sent a movement command to
the Tello — it was detection/visualization only. The refactored `main.py`
does call `drone.move()`, gated through `SafetyManager`. Conservative
defaults (`MAX_FORWARD_SPEED=0.3`, etc., in `app/config.py`) and a `mock`
default platform mean nothing flies unless you explicitly pass `--drone dji`
with an aircraft actually connected. See [TESTING.md](TESTING.md) before
ever doing that.

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
    dji_controller.py         # WebSocket client to android-bridge/ - see DRONE_BRIDGE.md
  safety/
    safety_manager.py        # connection-loss / stale-command / lost-person / battery / e-stop
archive/
  tello/                      # archived Tello backend, not wired into --drone - see its README
    tello_controller.py
    camera_test.py
    test_flight.py            # manual, real-hardware script - never auto-run by pytest
scripts/
  dji_smoke_test.py           # manual, real-hardware staged takeoff/move/land test for the Mini 3
tests/
  unit/                       # command conversion, validation, clamping, safety states
  integration/                 # detection(fixture boxes) -> tracking -> follow -> mock drone
```
