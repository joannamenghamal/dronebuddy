# DroneBuddy Bridge (Android)

Android companion app that bridges the Python autonomy process (this repo's
`app/`) to a DJI Mini 3 via the DJI Mobile SDK V5. Background and protocol
details live in [`../DRONE_BRIDGE.md`](../DRONE_BRIDGE.md) and
[`../DJI_MINI_3_SETUP.md`](../DJI_MINI_3_SETUP.md) — read those first.

All DJI SDK call shapes below have been cross-checked against the real
`dji-sdk-v5-aircraft-5.18.0` AAR (via `javap` on the cached Gradle
dependency jars, not guessed from docs/samples). `./gradlew assembleDebug`
has been run end-to-end against this project and produces a real
`app-debug.apk` — not just a Kotlin compile check. What's left unverified is
only what genuinely requires a registered DJI developer app key and/or a
physical aircraft to confirm — search the project for `UNVERIFIED` to see
exactly which spots those are and why.

## What's implemented vs. stubbed

| Piece | Status |
|---|---|
| Gradle project structure, AGP/Kotlin versions, dependency coordinates | Verified against Maven Central / `dl.google.com` metadata |
| `protocol/Protocol.kt` (JSON message encode/decode, command validation) | Implemented, matches `DRONE_BRIDGE.md` |
| `bridge/BridgeServer.kt` (WebSocket server: decodes/validates messages, routes them to `BridgeServer.Handler`, sends acks/telemetry/video, reports link loss; no DJI calls) | Implemented against `org.java-websocket` (verified library) |
| `dji/DjiCommandHandler.kt` (the app's `BridgeServer.Handler`: virtual stick, takeoff/land, stale-command hover) | Implemented; uses only the DJI classes below |
| `DroneBuddyApplication.kt` (DJI Helper install) | Implemented, call shape confirmed via `javap` |
| `dji/DjiSdkConnectionManager.kt` (SDKManager registration) | Implemented, `init()`/callback signature confirmed via `javap` |
| `dji/DjiVirtualStickController.kt` (flight control) | Implemented, `VirtualStickFlightControlParam` fields confirmed via `javap` |
| `dji/DjiTelemetryProvider.kt` (battery/GPS/attitude) | Implemented, `DJIKey` identifiers confirmed via `javap` |
| `dji/DjiFlightActions.kt` (takeoff/land) | Implemented — `KeyStartTakeoff`/`KeyStartAutoLanding` action-key calls, confirmed via `javap` |
| `dji/DjiCameraStreamProvider.kt` (live video) | Implemented — `CameraStreamManager.addFrameListener`, confirmed via `javap`; JPEG-encodes and pushes frames as binary WebSocket messages on the same bridge connection. `ComponentIndexType.LEFT_OR_MAIN` and realistic frame rate/latency are UNVERIFIED on a physical Mini 3 — see `DRONE_BRIDGE.md` |
| ProGuard rules | Best-effort keep rules, flagged unverified for 5.18.0 — can only be confirmed by actually running a release build |
| `res/xml/accessory_filter.xml` | Placeholder — copy DJI's own sample's filter; genuinely needs the real sample project to confirm |
| App launcher icon (`res/drawable/ic_launcher.xml`) | Placeholder vector drawable so the build doesn't depend on a missing asset — swap for real branding whenever, purely cosmetic |
| Manifest merge with DJI's AAR (`usesCleartextTraffic`) | Fixed — DJI's own AAR declares this `false`, which collided with ours (`true`, required since `DRONE_BRIDGE.md`'s protocol is plain `ws://`); resolved via `tools:replace` in `AndroidManifest.xml` |

## Before you can build this

1. **Get a DJI developer account and app key.** Register at
   [developer.dji.com](https://developer.dji.com) with the application ID
   that matches `namespace`/`applicationId` in `app/build.gradle.kts`
   (currently `com.example.visualbuddy`) — or register with a different ID
   and change `build.gradle.kts` to match. **The two must be identical**: DJI's
   registration server validates the requesting app's package name against
   the key's registered package, and a mismatch fails with
   `register_failure: INVALID_METADATA` at runtime (not at build time), which
   looks like a bad key even though the key itself is fine.
2. **Put the key in `local.properties`, not in source.** Copy
   `local.properties.example` to `local.properties` (already gitignored —
   Android Studio also writes your `sdk.dir` into this same file on first
   sync) and set:
   ```
   DJI_API_KEY=your_real_key_here
   ```
   `app/build.gradle.kts` reads this at build time and injects it into
   `AndroidManifest.xml`'s `com.dji.sdk.API_KEY` meta-data via
   `manifestPlaceholders` — the real key never touches git, and the build
   fails loudly with a clear message if `local.properties` is missing it.
3. **Copy the real `res/xml/accessory_filter.xml`** from DJI's own
   `Mobile-SDK-Android-V5` sample project — the vendor/model/version values
   here are a placeholder and were never independently verifiable from this
   environment.
4. **Build and install.** The Gradle wrapper is checked in, so no separate
   install step is needed for it. Two options:
   - **Command line** (fastest if you just want it on your phone): connect
     the Android phone via USB with USB debugging enabled, then from
     `android-bridge/`:
     ```
     ./gradlew installDebug
     ```
     This builds and installs `app-debug.apk` directly onto the connected
     device. Launch the app from the phone afterward (the "DroneBuddy
     Bridge" icon).
   - **Android Studio**: open `android-bridge/` and let it sync, then hit
     Run with the phone selected as the target device. Also the easier path
     if you hit SDK/NDK version mismatches it can auto-resolve.

## Running an end-to-end test with the physical Mini 3

1. **Physical setup.** Power on the Mini 3 and its RC, then connect the
   Android phone/tablet to the RC via USB. The accessory filter (step 3
   above) is what makes the bridge app auto-launch on that connection —
   until that's copied from DJI's sample, launch it manually instead.
2. **Confirm SDK registration.** On first launch with a real key and an
   internet-connected device, the app should register against DJI's
   servers (via `DjiSdkConnectionManager`) and then report the aircraft
   connected once the RC/USB link is live. The on-screen status text
   (`MainActivity`) shows SDK/aircraft/bridge state live — watch `adb
   logcat` too if something doesn't come up. A key that doesn't match the
   registered `applicationId` will fail here specifically, not at build time.
3. **Find the device's IP.** The bridge server listens on `0.0.0.0:8765`
   on the Android device. Get that device's IP on the network it shares
   with the computer running the Python side (phone Settings → Wi-Fi →
   network details, or `adb shell ip addr`).
4. **Point the Python side at it.** `app/config.py` reads these straight
   from the environment (nothing loads `.env` automatically — it's a
   reference, not a loaded file), so export them in the shell you'll run
   Python from:
   ```
   export DRONE_PLATFORM=dji
   export BRIDGE_HOST=<android device's IP>
   export BRIDGE_PORT=8765
   ```
   Both machines need to be on the same network/Wi-Fi for this to connect.
5. **Run the Python process**: `python3 -m app.main --drone dji` (or just
   `python3 -m app.main` if `DRONE_PLATFORM=dji` is set via env vars).
   `DJIController.connect()` will raise `ConnectionError` if it can't reach
   the bridge within 10s — confirm the IP/port and that both devices are on
   the same network first if that happens.
6. **Start conservative.** Keep the Mini 3 low and in a wide-open outdoor
   space for the first run — nothing here has been tested against a real
   aircraft yet. Run the staged smoke test before trusting the full
   follow-me loop:
   ```
   python3 -m scripts.dji_smoke_test
   ```
   It connects, prints telemetry for a few seconds, then asks for a typed
   `y` before each flight-affecting step (confirming the aircraft is
   already airborne, then a small `up`/`forward`/`yaw` nudge each, then
   `land()`) — nothing happens without an explicit confirmation at each
   stage. Note `app/main.py` itself never calls `takeoff()`: the follow-me
   loop only ever sends `move()`/`land()`/`emergency_stop()`, so the
   aircraft needs to already be airborne (manual RC takeoff) before you
   start it, exactly as the smoke test assumes.
7. **Know your kill switches.** The RC's own physical controls and DJI's
   firmware-level failsafes (RC signal loss, geofencing, low battery RTH)
   are never bypassed by this bridge and are always the fastest way to
   regain control if anything looks wrong — don't rely on `emergency_stop()`
   as the primary safety mechanism; see `DRONE_BRIDGE.md` for exactly what
   it does and does not guarantee.
