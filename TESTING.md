# Testing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the test suite

```bash
pytest
```

`pytest.ini` sets `pythonpath = .` (so `from app...` resolves without extra
`PYTHONPATH` juggling). The one manual, real-hardware script that used to
live under `tests/` (`test_flight.py`, for the now-archived Tello backend)
has moved to `archive/tello/test_flight.py` and is outside `testpaths`
entirely, so there's nothing to ignore here anymore.

## What's covered

**Unit** (`tests/unit/`)
- `test_movement_command.py` — clamping to `[-1.0, 1.0]`, `NaN`/`Infinity`
  rejection, zero-command detection.
- `test_follow_controller.py` — direction/distance -> `MovementCommand`
  conversion, and that the display string (`get_drone_action`) and the
  velocity vector (`get_movement_command`) never disagree on direction.
- `test_safety_manager.py` — stale-command detection, connection-loss
  detection (including "no telemetry ever received"), lost-person detection,
  low-battery -> land, emergency-stop latching (and that it does *not*
  self-clear), invalid-command rejection, output clamping. Uses a fake clock
  so timeout tests are deterministic and instant.
- `test_mock_controller.py` — `MockDroneController` lifecycle and that it
  actually records commands (test infrastructure needs testing too, since
  every other test in this suite depends on it being correct).

**Integration** (`tests/integration/`)
- `test_pipeline_mock.py` — fixed bounding boxes (standing in for YOLO
  output, so the test is deterministic and doesn't need model weights or a
  camera) through the *real* `person_tracker` and `follow_controller` code,
  through `SafetyManager`, into a `MockDroneController`. Verifies the
  direction/distance a synthetic detection implies actually produces the
  expected velocity signs, and that losing the person falls back to hover.

## Running the pipeline without hardware

```bash
python -m app.main --drone mock
```

Runs the full detection -> tracking -> follow -> safety -> drone loop against
`MockDroneController`, using your laptop webcam via OpenCV/YOLO for real
detections but never sending a command anywhere near real hardware. This is
the first thing to run after any change to the follow-me or safety logic.

## Ground-testing procedure before any real flight

Only after the steps above pass:

1. **DJI Mini 3, propellers off or drone restrained**, once `DJIController`
   and the Android bridge exist. Confirm `connect()`, `get_telemetry()`, and
   `get_video_frame()` work, and that `drone.move()` calls (watch the
   console/log output) look correct for a person walking in frame, before
   trusting it to actually fly. See [DRONE_BRIDGE.md](DRONE_BRIDGE.md)'s
   heartbeat/stale-command/connection-loss behavior specifically.
2. **DJI Mini 3, open area, low battery threshold verified.** Take off
   manually via the RC, confirm the low-battery `LAND` path works by
   watching `SafetyManager` logs as the battery naturally drains near the
   end of a flight — don't rely on this being correct after propellers are
   already spinning near people or obstacles.
3. **Emergency stop drill.** Before flying near any person, confirm
   `SafetyManager.trigger_emergency_stop()` reachable from wherever the
   operator will actually be (currently: nowhere convenient — there is no
   keyboard/RC hook wired to it yet; wire one before this step is meaningful).

The Tello backend used to give a cheap way to rehearse steps 1-3 indoors
before trying them on the Mini 3; it's archived under
[archive/tello/](archive/tello/README.md) and can be revived for that
purpose if useful (see that README for how).

Do not skip from step 1 directly to unattended autonomous flight near a
person. The existing safety timeouts are conservative but untested against
real radio conditions.
