# DroneBuddy (Visual Buddy)

A DJI Mini 3 follows a visually impaired user and tells them what's around
them out loud: people approaching, objects in their path, and where things
are when they ask.

```
Laptop (Python, app/)  <--Wi-Fi-->  Phone (Android app, android-app/)  <--controller-->  DJI Mini 3
 detection, tracking,                bridge: passes messages,
 alerts, safety, follow              flies the drone, sends video
```

## What's where

| Folder | What it is |
|---|---|
| `app/` | The laptop program: detection, user tracking, alerts, audio, safety, follow control |
| `android-app/` | The phone app: connects to the drone and runs the bridge the laptop talks to. See [android-app/README.md](android-app/README.md) |
| `tests/` | Python tests |
| `scripts/` | `bridge_check.py` (tests the phone app without flying), `dji_smoke_test.py` (step-by-step first flight) |
| `tools/` | `analyze_clip.py`: runs a recorded video through the pipeline |
| `android-bridge/` | The earlier standalone bridge app, kept until `android-app/` is tested with the drone |

## 1. Set up the laptop (once)

Needs Python 3.11 or newer.

```
git clone https://github.com/joannamenghamal/dronebuddy.git
cd dronebuddy
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The first run downloads the detection model (`yolo11n.pt`), so be online for it.

## 2. Run without the drone

Uses the laptop camera as the drone's camera. Nothing flies.

```
python3 -m app.main --drone mock
```

- `--source 1`: use a different camera, if 0 is the wrong one.
- `--source path/to/clip.mp4`: play a recorded drone clip instead of a camera.
- `--mute`: print alerts instead of speaking them.
- `--voice-script "4:WHERE_IS:car, 9:REPEAT"`: fake voice commands at those
  seconds, until the phone's microphone is hooked up.

In the window: **SPACE** is the emergency stop (the drone hovers), **q** quits.

## 3. Run with the drone

1. **Phone:** build and install the app from `android-app/` (setup in
   [android-app/README.md](android-app/README.md)). Plug the drone's controller
   into the phone, turn on the drone, and open the app. Its Logs screen should
   show "Python Bridge: Bridge running".
2. **Find the phone's IP:** Settings → Wi-Fi → your network. The phone and
   laptop must be on the same Wi-Fi.
3. **Check the connection without flying:**
   ```
   python3 -m scripts.bridge_check --host <phone ip>
   ```
   Every line should say PASS.
4. **Fly:** take off by hand with the controller first, then:
   ```
   BRIDGE_HOST=<phone ip> python3 -m app.main --drone dji
   ```
   (Windows PowerShell: `$env:BRIDGE_HOST="<phone ip>"; python -m app.main --drone dji`)

Keep a hand on the controller. Its sticks and DJI's own safety features
always work and are the fastest way to take back control. The laptop lands
the drone if it loses sight of the user for 5 seconds, or when the battery
drops to 20%.

## Run the tests

```
pytest
```

## Settings

All optional, set as environment variables. See `.env.example` for the full
list. The main ones:

| Variable | Default | What it does |
|---|---|---|
| `BRIDGE_HOST` | `127.0.0.1` | The phone's IP address |
| `CAMERA_INDEX` | `0` | Laptop camera for `--drone mock` |
| `MAX_FORWARD_SPEED` | `0.3` | Fraction of the drone's top speed (kept low on purpose) |
| `LOST_PERSON_LAND_TIMEOUT_S` | `5.0` | Land after losing the user this long |
| `MIN_BATTERY_PERCENT` | `20` | Land at this battery level |

## More docs

- [ARCHITECTURE.md](ARCHITECTURE.md): how the laptop program is built
- [SAFETY.md](SAFETY.md): every safety rule and what triggers it
- [DRONE_BRIDGE.md](DRONE_BRIDGE.md): the messages between laptop and phone
- [BRIDGE_INTEGRATION.md](BRIDGE_INTEGRATION.md): how the bridge fits into an Android app
- [DJI_MINI_3_SETUP.md](DJI_MINI_3_SETUP.md): DJI developer account and SDK notes
- [TESTING.md](TESTING.md): what the tests cover
