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

## Voice commands without the phone

Until the phone app sends voice commands, `--voice-script` plays scripted
ones at set seconds after start (`FakeMic`):

```bash
python -m app.main --drone mock --source videos/clip2.mp4 \
    --voice-script "4:WHERE_IS:car, 8:QUIETER, 10:REPEAT, 14:STOP_SESSION"
```

Each command is answered out loud and logged (`voice_command`,
`voice_answer`); `STOP_SESSION` ends the session. Add `--mute` to log the
answers instead of speaking them.

On `--drone dji`, commands come from the phone instead (`MicInput`) and the
phone speaks (`BridgeSpeech`); `tests/unit/test_dji_controller.py`
exercises that round trip against the fake bridge.

## Checking a recorded drone clip

```bash
python tools/analyze_clip.py videos/clip1.mp4
```

Runs the whole pipeline on a recorded video with no window or speech, prints
what it detected, how far away the user was and every alert, and saves an
annotated copy of the video. Run it on real Mini 3 footage to see what the
drone would do before it flies.

## Flight-test procedure

In order, each step only once the one before it works. Steps 1-2 can't make
the drone fly.

1. **Connection, drone on the ground, motors off.** Open the phone app with
   the drone connected (Logs: "Bridge running"), then from the laptop:
   ```bash
   python -m scripts.bridge_check --host <phone ip> --save-frame frame.jpg
   ```
   Every line PASS; `frame.jpg` is the drone's camera view.
2. **The real program, still on the ground.** `BRIDGE_HOST=<phone ip> python
   -m app.main --drone dji` and walk in front of the drone's camera. Check the
   video, the tracking boxes and the `Command:` line in the panel make sense.
   Press SPACE once to see the emergency stop show up, then quit with `q`.
3. **Taking back control.** Take off by hand and hover at eye height. Start
   the laptop program (the phone's Logs say "Virtual stick on"), then check
   both ways out: quit it with `q` and confirm the sticks fly the drone again
   ("Virtual stick off"); start it again and press the controller's Pause
   button. Don't go on until you know which one works.
4. **Tiny moves.** Hovering after a hand takeoff:
   ```bash
   BRIDGE_HOST=<phone ip> python -m scripts.dji_smoke_test
   ```
   It asks for `y` before each 1-second move (about 20 cm up, 40 cm forward,
   a 6° turn) and before landing. Check each goes the right way.
5. **Following.** Open area, low, two people: one being followed, one on
   the controller ready to take over. For the first runs, lower the speeds:
   ```bash
   MAX_FORWARD_SPEED=0.1 MAX_LATERAL_SPEED=0.1 MAX_YAW_RATE=0.1 \
       BRIDGE_HOST=<phone ip> python -m app.main --drone dji
   ```

6. **Low battery.** Near the end of a flight, watch the laptop's log as the
   battery drains toward `MIN_BATTERY_PERCENT` (20%) and confirm it lands.
   Don't count on this before you've seen it work.

The archived Tello backend ([archive/tello/](archive/tello/README.md)) can be
revived to rehearse steps 3-5 indoors before trying them on the Mini 3.

Don't skip from step 1 to unattended autonomous flight near a person. The
safety timeouts are conservative but untested against real radio
conditions. See [SAFETY.md](SAFETY.md) for what's still open.
