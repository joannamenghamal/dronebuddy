# DroneBuddyApp

The team's Android app. It connects to the DJI Mini 3 through the DJI SDK, and
the laptop (Python, `app/` in the repo root) controls the drone through it.
How the app is organized: [ARCHITECTURE.md](ARCHITECTURE.md).

## The bridge is already in this app

You don't need to add or copy anything. The bridge is the part that lets the
laptop talk to this app over Wi-Fi:

| File | What it does |
|---|---|
| `bridge/BridgeServer.kt` | Listens for the laptop on port 8765 and passes messages both ways. Never calls the DJI SDK itself |
| `bridge/Protocol.kt` | The message formats (see [DRONE_BRIDGE.md](../DRONE_BRIDGE.md)) |
| `dronecontrollers/DjiCommandHandler.kt` | Turns the laptop's commands into drone actions, and hovers if the laptop disconnects or goes quiet |
| `dronecontrollers/DjiVirtualStickController.kt` | Flies the drone at the speeds the laptop asks for, capped at 2 m/s |
| `dronecontrollers/DjiFlightActions.kt` | Takeoff and landing |
| `dronecontrollers/DjiCameraStreamProvider.kt` | Sends the drone's camera to the laptop |
| `dronecontrollers/DjiTelemetryProvider.kt` | Sends battery, position, heading and speed to the laptop |
| `audio/SpeechPlayer.kt` | Speaks the laptop's alerts out loud |

`DroneManagerViewModel` starts all of this when the app opens. When the drone
connects, it starts the camera and telemetry.

**Virtual stick is on only while both the drone and the laptop are
connected.** Then the app flies the drone and the controller's sticks are
ignored. The rest of the time the controller flies it as normal: you can take
off by hand before starting the laptop program, and you get the sticks back as
soon as the laptop program quits, or within 3 seconds if the laptop goes
silent (closed, frozen, off the Wi-Fi). The Logs screen says
"Virtual stick on" / "Virtual stick off" each time it switches.

**Adding something new for the laptop** (a new piece of drone data, a new
command): keep using `DroneManager` and the ViewModel like the rest of the app,
and add the message to `bridge/Protocol.kt` and `DRONE_BRIDGE.md`, so the
Python side knows about it.

## Setup

1. Put the DJI key in `local.properties` (gitignored, never committed):
   ```
   DJI_APP_API_KEY=your_key_from_developer.dji.com
   ```
   The key must be registered for this app's package, `com.example.dronebuddyapp`.
2. Open `android-app/` in Android Studio, let it sync, and run it on the phone.
3. Copy the real `res/xml/accessory_filter.xml` from DJI's MSDK V5 sample app.
   The one here is a placeholder, so the app may not open by itself when the
   controller is plugged in. Opening it by hand works.

## Checking the bridge

1. Connect the drone's controller to the phone and open the app. The Home
   screen shows the app and drone connection status. Bridge events show in
   Logs under "Python Bridge".
2. Find the phone's IP: Settings → Wi-Fi → your network.
3. On a laptop on the same Wi-Fi, from the repo root:
   ```
   python3 -m scripts.bridge_check --host <phone ip> --save-frame frame.jpg
   ```
   This doesn't fly the drone. It prints PASS/FAIL for each part, and
   `frame.jpg` should be the drone's camera view.
4. Then the real thing: `BRIDGE_HOST=<phone ip> python3 -m app.main --drone dji`.
   Take off by hand first; the laptop only moves the drone once it's flying.
