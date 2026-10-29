# Connecting an Android app to the bridge

For anyone building the Android (Kotlin) app that flies the drone and wants
the Python side (`app/`) to control it. The wire format itself is in
[DRONE_BRIDGE.md](DRONE_BRIDGE.md); this is the how-to.

```
Python (laptop)  <--WebSocket, port 8765-->  your Android app  <--DJI MSDK V5-->  Mini 3
  DJIController         client                 BridgeServer + your Handler
```

Your app runs the server, Python connects to it. `BridgeServer` handles
the socket, JSON, validation and acks. Your app does everything that
touches the drone, by implementing one interface: `BridgeServer.Handler`.
`android-bridge/` is a complete working example of all of this.

## 1. Add the bridge to your app

Copy these two files into your project:

- `android-bridge/app/src/main/java/com/dronebuddy/bridge/bridge/BridgeServer.kt`
- `android-bridge/app/src/main/java/com/dronebuddy/bridge/protocol/Protocol.kt`

Keep their `package` lines, or change both together (`BridgeServer.kt`
imports `com.dronebuddy.bridge.protocol.*`).

Add the WebSocket library to `app/build.gradle.kts`:

```kotlin
dependencies {
    implementation("org.java-websocket:Java-WebSocket:1.5.6")
}
```

In `AndroidManifest.xml`, allow network access and plain `ws://`. DJI's
own manifest sets `usesCleartextTraffic="false"`, so you need
`tools:replace` or the socket is silently blocked:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:usesCleartextTraffic="true"
        tools:replace="android:usesCleartextTraffic"
        ...>
```

## 2. Implement the Handler

```kotlin
interface Handler {
    fun onClientConnected()
    fun onClientDisconnected()
    fun onLinkLost()
    fun onFlightCommand(command: BridgeMessage.FlightCommand)
    fun onEmergencyStop()
    fun onTakeoff(reply: (ok: Boolean, detail: String?) -> Unit)
    fun onLand(reply: (ok: Boolean, detail: String?) -> Unit)
}
```

| Method | Called when | What your app must do |
|---|---|---|
| `onClientConnected` | Python connects | Hover |
| `onClientDisconnected` | Socket closes or errors | Hover |
| `onLinkLost` | Socket open but no message for 3s | Hover |
| `onFlightCommand` | Every movement command (~10-30/s) | Fly at that velocity, and note the time |
| `onEmergencyStop` | User pressed SPACE / safety layer says stop | Hover immediately |
| `onTakeoff` / `onLand` | Python asks | Start the DJI action, then call `reply` **exactly once** with the result. Don't hover until the next flight command (see below) |

`FlightCommand` has `forward`, `right`, `up`, `yaw`, each already checked
to be finite and within `[-1.0, 1.0]`: fractions of your own max speed,
not m/s. Scale them in your app (`DjiVirtualStickController.sendVelocity`
does this with conservative caps of 2 m/s, 1 m/s and 30°/s).

**Also required: the 1-second hover.** If no `onFlightCommand` arrives for
1 second while Python is connected, hover. Python sends a command every
frame, so a gap means it froze. Heartbeats don't count. `BridgeServer`
doesn't do this for you, because it's about flying.

**But not during takeoff or landing.** After asking to land, Python stops
sending commands on purpose, and hover inputs sent during DJI's
auto-landing or takeoff can cancel it. From `onTakeoff`/`onLand` until
the next `onFlightCommand` (or `onEmergencyStop`), skip the 1-second
hover and the hovers on disconnect and link loss. The drone holds
position on its own without stick input.

**Don't block** in any of these methods. They run on the WebSocket
server's threads (`onLinkLost` on its watchdog timer), and blocking stalls
every other message. For takeoff/land, start the action and call `reply`
from the DJI callback. `reply` is safe to call from any thread, even after
Python has disconnected (the ack is then dropped).

The quickest route is to copy `android-bridge`'s implementation:
`dji/DjiCommandHandler.kt` (the Handler, with the 1-second hover), plus
`dji/DjiVirtualStickController.kt` and `dji/DjiFlightActions.kt`, which it
uses. Or write your own along these lines:

```kotlin
class MyDroneHandler(private val drone: MyDroneControls) : BridgeServer.Handler {
    @Volatile private var connected = false
    @Volatile private var lastCommandAtMs = 0L
    @Volatile private var takingOffOrLanding = false
    private val timer = Timer("stale-command", true)

    fun start() {
        timer.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                if (connected && !takingOffOrLanding &&
                    System.currentTimeMillis() - lastCommandAtMs >= 1000L) drone.hover()
            }
        }, 200L, 200L)
    }

    fun stop() = timer.cancel()

    override fun onClientConnected() { connected = true; lastCommandAtMs = System.currentTimeMillis(); drone.hover() }
    override fun onClientDisconnected() { connected = false; if (!takingOffOrLanding) drone.hover() }
    override fun onLinkLost() { if (!takingOffOrLanding) drone.hover() }
    override fun onEmergencyStop() { takingOffOrLanding = false; drone.hover() }

    override fun onFlightCommand(command: BridgeMessage.FlightCommand) {
        takingOffOrLanding = false
        lastCommandAtMs = System.currentTimeMillis()
        drone.velocity(command.forward, command.right, command.up, command.yaw)
    }

    override fun onTakeoff(reply: (Boolean, String?) -> Unit) {
        takingOffOrLanding = true
        drone.takeoff { ok, error -> if (!ok) takingOffOrLanding = false; reply(ok, error?.toString()) }
    }

    override fun onLand(reply: (Boolean, String?) -> Unit) {
        takingOffOrLanding = true
        drone.land { ok, error -> if (!ok) takingOffOrLanding = false; reply(ok, error?.toString()) }
    }
}
```

Virtual stick must be enabled (`VirtualStickManager.enableVirtualStick`)
once the aircraft connects, or velocity commands do nothing.

## 3. Start the server, send telemetry and video

```kotlin
val handler = MyDroneHandler(drone).also { it.start() }
val server = BridgeServer(port = 8765, handler = handler)   // Python's default port
server.start()

// Whenever telemetry changes (android-bridge pushes on every DJI key update):
server.sendTelemetry(
    BridgeMessage.Telemetry(
        battery = 82,              // percent; use null, not 0, when unknown
        connected = true,          // is the DRONE connected (not the socket)
        latitude = null, longitude = null,
        altitude = 1.5,            // m
        heading = 90.0,            // degrees
        velocityX = 0.0, velocityY = 0.0, velocityZ = 0.0,   // m/s
        timestampEpochMs = System.currentTimeMillis(),
    )
)

// Each camera frame, as JPEG bytes:
server.sendVideoFrame(jpegBytes)

// On shutdown:
server.shutdownServer()
handler.stop()
```

Both send methods do nothing when Python isn't connected, so you can call
them unconditionally.

- **Telemetry**: send it whenever values change, at least a few times a
  second. Python lands the drone when `battery` drops to 20% or below.
- **Video** is JPEG bytes, one frame per call. About 10 fps is plenty
  (that's what the follow loop can process); keep each frame under 16 MB
  (typically 100-300 KB at quality 70).

For the DJI camera feed, copy `dji/DjiCameraStreamProvider.kt`, and start
it **after the aircraft connects**, not at app launch. If your app doesn't
show the video on screen, `CameraStreamManager.setKeepAliveDecoding(true)`
is required: without a display Surface, MSDK doesn't decode and your frame
listener never fires. `DjiCameraStreamProvider` already does this.

## 4. Test it without flying

Phone and laptop on the same Wi-Fi. Find the phone's IP (Settings → Wi-Fi
→ network details). From the repo root on the laptop:

```
python3 -m scripts.bridge_check --host <phone ip> --save-frame frame.jpg
```

It runs for 10 seconds and sends only heartbeats, all-zero (hover)
commands, and one out-of-range command your app must reject. It never
sends takeoff, land or emergency stop. Then it prints PASS/FAIL for:
acks, the rejection, telemetry rate and fields, whether the drone is
connected, and video frame rate, size and JPEG validity. `frame.jpg` is
the last frame it received; open it to check it's really the drone's
camera.

Once every line passes:

1. `python3 -m app.main --drone dji` with `BRIDGE_HOST=<phone ip>` shows
   the video with tracking on top. The drone needs to already be in the
   air (manual takeoff) before this sends any movement.
2. `python3 -m scripts.dji_smoke_test` for a staged flight test. It asks
   before every step.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `bridge_check` can't connect | Different Wi-Fi networks, wrong IP, app not running, or the manifest is missing `usesCleartextTraffic` + `tools:replace` |
| Connects, but telemetry says `connected=False` | DJI SDK registration failed. The app key must be registered for your app's exact `applicationId`. Look for `register_failure` in `adb logcat` |
| No video frames | Camera listener started before the aircraft connected, or keep-alive decoding is off (see step 3) |
| Video frames not decodable | Sending raw RGBA/YUV bytes instead of JPEG |
| Out-of-range command not rejected | Commands aren't going through `BridgeServer`/`ProtocolCodec` |
| `app.main` says "no video from the DJI bridge after 10s" | Same as "No video frames" |
