# DJI Mini 3 Setup — Compatibility & Handoff Notes

Status: **implemented.** `android-bridge/` now contains a real Android
project built against these findings, with every DJI SDK call shape listed
below cross-checked via `javap` against the actual `dji-sdk-v5-aircraft-5.18.0`
AAR (not just docs/search results). This document still records what's
verified vs. not, so nothing here is mistaken for confirmed-on-hardware —
compiling cleanly against the SDK is not the same as flying a real Mini 3.

## Rule this document follows

> For every capability: DJI SDK supports it + Mini 3 supports it + the
> current SDK version supports it = implementable. If any part is uncertain,
> it's marked UNVERIFIED here, not assumed.

## Verified

| Question | Answer | Source |
|---|---|---|
| Does Mobile SDK V5 list the base **DJI Mini 3** (not Mini 3 Pro) as a supported aircraft? | **Yes** — listed separately from "DJI Mini3 Pro" and "DJI Mini 4 PRO" in the current supported-products list. | `dji-sdk/Mobile-SDK-Android-V5` repo, developer.dji.com |
| Current SDK version | **5.18.0** (Android), as of this writing | developer.dji.com / GitHub releases |
| Does the SDK support Android, iOS, or both? | Android and iOS; **no desktop or Python binding** — this is why a bridge process is required at all, not optional | developer.dji.com |
| Is Virtual Stick control available for Mini 3? | **Yes** — `IVirtualStickManager` has been available since MSDK 5.0.0, with Mini-3-specific fixes shipped as recently as v5.10.0 (confirms it's actively maintained for this aircraft, not just nominally listed) | developer.dji.com API reference, SDK release notes |
| DJI Helper install call shape (`DroneBuddyApplication.kt`) | Confirmed | `javap` against `dji-sdk-v5-aircraft-provided:5.18.0` |
| `SDKManager` registration `init()`/callback signature (`DjiSdkConnectionManager.kt`) | Confirmed | `javap` against the same AAR |
| `VirtualStickFlightControlParam` field names/types (`DjiVirtualStickController.kt`) | Confirmed | `javap` against the same AAR |
| Telemetry `DJIKey` identifiers used (`DjiTelemetryProvider.kt`) | Confirmed | `javap` against the same AAR |
| `KeyStartTakeoff`/`KeyStartAutoLanding` exist as `DJIActionKeyInfo<EmptyMsg, EmptyMsg>` on `DJIFlightControllerKey`, and the `create()`/`action()` call shapes used to invoke them (`DjiFlightActions.kt`) | Confirmed | `javap` against the same AAR |
| `CameraStreamManager.getInstance().addFrameListener(ComponentIndexType, FrameFormat, CameraFrameListener)` exists, and `CameraFrameListener.onFrame(ByteArray, offset, length, width, height, FrameFormat)` is the callback shape; `FrameFormat.RGBA_8888` is a valid enum value (`DjiCameraStreamProvider.kt`) | Confirmed | `javap` against `dji-sdk-v5-aircraft-provided:5.18.0` |

## UNVERIFIED — can only be resolved with a registered app key and/or physical hardware

1. **Exact telemetry *values* returned for the base Mini 3 specifically at
   runtime.** The DJIKey identifiers themselves are confirmed to exist on the
   SDK (see above), but the Mini 3 (unlike Mini 3 Pro) has no obstacle-sensing
   hardware — some perception-related keys may always report "unsupported"
   on the base Mini 3 even though they compile and resolve fine. Only a live
   aircraft can confirm this.
2. **Realistic video frame rate/latency for Mini 3 via SDK V5, and whether
   `ComponentIndexType.LEFT_OR_MAIN` is the index the aircraft actually
   reports.** The call shape is confirmed (see above) and both sides are
   implemented — `DjiCameraStreamProvider.kt` streams JPEG-encoded frames
   over the bridge WebSocket, `DJIController.get_video_frame()` decodes
   them — but glass-to-app latency, sustainable frame rate over a real
   WiFi link between two devices, and whether `LEFT_OR_MAIN` is correct for
   the base Mini 3 specifically (it's what DJI's own samples bind for
   single-camera aircraft, not confirmed against this aircraft) all need a
   physical unit to verify. See `DRONE_BRIDGE.md`'s "Video" section.
3. **Virtual Stick arming preconditions on Mini 3** — e.g. minimum GPS
   satellite count, whether it degrades gracefully or refuses input entirely
   without GPS lock, and any firmware-enforced speed/attitude caps that could
   silently clip values sent from `MAX_FORWARD_SPEED`/etc.
4. **Whether the SDK exposes anything distinct from a forced virtual-stick
   hover that qualifies as a true "emergency stop" / motor cutoff** for this
   aircraft. `BridgeServer`'s current `emergency_stop` handling only forces a
   hover (see `DRONE_BRIDGE.md`) — it does not claim to cut power, and this
   can't be confirmed further without a physical aircraft.
5. **Region/firmware feature gating.** DJI has historically shipped
   country-specific restrictions (e.g. geofencing behavior, altitude caps).
   Needs checking against the specific firmware/region the physical unit will
   run in.
6. **Whether registration actually succeeds against a real, issued app key.**
   The registration *call shape* is confirmed (see above); whether DJI's
   servers actually accept a given app key/package name combination, and what
   the first-run internet-connectivity requirement looks like in practice,
   can only be confirmed by registering a real app and running it.
7. **ProGuard/R8 keep rules for release builds.** Written as best-effort for
   5.18.0 but never exercised through an actual release build — only a real
   build run (or an obfuscation-related crash) can confirm they're sufficient.
8. **The RC USB accessory filter** (`res/xml/accessory_filter.xml`) — the
   vendor/model/version values are a placeholder; DJI's own
   `Mobile-SDK-Android-V5` sample project has the authoritative filter and
   should be copied in before relying on auto-launch-on-connect.

## What's left before flying this for real

- Register a real DJI developer app key for `com.dronebuddy.bridge` (or
  whatever package name is used) and drop it into `AndroidManifest.xml` in
  place of the `REPLACE_WITH_DJI_APP_KEY` placeholder.
- Copy the real `accessory_filter.xml` from DJI's sample project.
- Build and install on the teammate's Android device, connect it to the RC,
  and confirm items 1-5 above against that specific physical Mini 3 and its
  firmware — SDK docs and `javap` describe what the SDK *supports*, not what
  a specific unit's firmware currently exposes.
- Only then treat `emergency_stop`, telemetry accuracy, and virtual-stick
  arming as validated rather than best-effort.
