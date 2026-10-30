# DroneBuddy

An Android app (Kotlin, min SDK 24) for connecting to and controlling drones. A single home activity hosts a set of fragments, one per screen. Drone connections live in a shared ViewModel, and a global log records anything important.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  HomeActivity                   │
│        (single activity, swaps fragments)       │
│                                                 │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │  Fragment │  │  Fragment │  │ LogFragment│  │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │
└─────────┼──────────────┼──────────────┼─────────┘
          │              │              │
          ▼              ▼              ▼
  ┌─────────────────────────────┐  ┌─────────────┐
  │  DroneControllerViewModel   │  │   LogItem   │
  │  (shared, activity-scoped)  │  │  (global)   │
  └─────────────────────────────┘  └─────────────┘
```

Three pieces:

1. **HomeActivity** is the only activity. It owns the fragment container and handles navigation between screens.
2. **DroneControllerViewModel** holds the drone references and connections. It is scoped to the activity, so every fragment sees the same instance.
3. **LogItem** is a global log object. Any class can write to it, and `LogFragment` displays it.

## TLDR
The important part everyone needs to know:
To access ANYTHING on the drone, you must go through the bridge, which will give you access to the DJI Drone Managers.
These **Managers** will give you access to anything on the drone, from coordinates to joystick control, etc. 

Tell me (Jeremy) what functionality you need, and I will create the keys/connections accessible through the DroneControllerViewModel.  Then we will connect it all together through the bridge.

Another important note is the logging, please use the logger as much as you can so that I can see what is happening on your side of the python in the android app.
It's simple, give it a string tag, the content of the message, and whether or not its a LOG, WARNING, or an error.

## Home Activity

`HomeActivity` does not contain screen logic. It hosts a fragment container and swaps fragments in and out.

```kotlin
supportFragmentManager.beginTransaction()
    .replace(R.id.container, SomeFragment())
    .addToBackStack(null)
    .commit()
```

Each screen is its own fragment. To add a screen:

1. Create the fragment and its layout.
2. Add a navigation entry point (button, menu item or bottom nav item).
3. Swap it into the container as shown above.

## Drone Controller ViewModel

`DroneControllerViewModel` is the single source of truth for drone state: which drones exist, which are connected, and the connection objects used to talk to them.

Fragments get the shared instance with `activityViewModels()`:

```kotlin
class SomeFragment : Fragment(R.layout.fragment_some) {

    private val droneController: DroneControllerViewModel by activityViewModels()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        // use droneController here
    }
}

## Drone Layer

Drone functionality is split into three classes, each with one job:

```
   Fragments
       │  observe state / send actions
       ▼
 ┌──────────────┐
 │ DroneViewModel│   shared, activity-scoped
 └──────┬───────┘
        │
        ├──────────────► DroneConnectionControl   (connects / disconnects via the SDK)
        │
        └──────────────► DroneManager             (holds SDK keys, reads drone info)
```
### DroneConnectionControl

Handles the **SDK connection lifecycle**. It is the only class that talks to the SDK to connect or disconnect.

- Registers with the SDK and starts or stops connections
- Reports connection state changes (connected, disconnected, failed)
- Logs every connection event with `LogItem`

Nothing outside this class should call SDK connection methods directly.

### DroneManager

Holds **references to the SDK keys** used to read information from the drone, such as battery, GPS, flight mode and signal strength.

- Single place where keys are defined, so they are not scattered across fragments
- Provides ways to read or listen to drone info through those keys
- Does not manage connections. That is `DroneConnectionControl`'s job

When you need a new piece of drone data, add its key here.

### DroneViewModel

The **single source of truth for drone state in the UI**. It is scoped to the activity, so every fragment sees the same instance. It coordinates the other two classes and exposes their results to fragments.

- Owns instances of `DroneConnectionControl` and `DroneManager`
- Exposes connection state and drone info as `LiveData` or `StateFlow`
- Receives user actions from fragments (connect, disconnect, and so on) and forwards them to the right class

Fragments get the shared instance with `activityViewModels()`:

```kotlin
class SomeFragment : Fragment(R.layout.fragment_some) {

    private val droneViewModel: DroneViewModel by activityViewModels()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        // observe droneViewModel state here
    }
}
```

### Rules

- **Always use `activityViewModels()`**, never `viewModels()`. `viewModels()` creates a separate instance per fragment, so the connection state would not be shared.
- **Fragments never touch the SDK, `DroneConnectionControl` or `DroneManager` directly.** They go through `DroneViewModel`.
- **Do not store connections or SDK keys in fragments.** Fragments are destroyed and recreated often, and the ViewModel survives configuration changes such as rotation.
- **Do not hold Views or Fragment references** in the ViewModel or either helper class, to avoid memory leaks.
- **Log connection events.** Anything that connects, disconnec
```

Rules:

- **Always use `activityViewModels()`**, never `viewModels()`. `viewModels()` creates a separate instance per fragment, and the connections would not be shared.
- **Do not store connections in fragments.** Fragments are destroyed and recreated often, and the ViewModel survives configuration changes such as rotation.
- **Do not hold Views or Fragment references in the ViewModel.** This causes memory leaks.
- Expose state as `LiveData` or `StateFlow` so fragments can observe it.

## Logging

`LogItem` is a global, in-memory log that can be called from anywhere. **Use it for anything important**, especially connections and failures.

### Writing a log

```kotlin
LogItem.addItem(LogItem.Status.INFO, "Connection", "Drone 1 connected")
LogItem.addItem(LogItem.Status.WARNING, "Battery", "Drone 1 at 20%")
LogItem.addItem(LogItem.Status.ERROR, "Connection", "Drone 2 lost signal")
```

### Levels

| Status    | Use for                                         |
|-----------|-------------------------------------------------|
| `INFO`    | Normal events: connected, disconnected, started |
| `WARNING` | Something unusual that is not fatal             |
| `ERROR`   | Failures that need attention                    |

### What to log

- Drone connects, disconnects and connection failures
- Commands sent to a drone, and their results
- Anything you would want to see when debugging a flight

### Viewing logs

`LogFragment` shows the log in a RecyclerView. Each row displays the timestamp, status, tag and message, with the message colored by status. New entries appear live while the fragment is open. If the fragment is not open, entries are still stored and show up when it is opened.

### Notes

- Call `LogItem.addItem` from the **main thread**. From a background thread, wrap it in `runOnUiThread { }` or post to the main looper, because the adapter update must run on the main thread.
- The log is **in memory only**. It is cleared when the app process is killed.
- Use a short, consistent `tag` per area (for example `"Connection"`, `"Battery"`, `"Command"`) so entries are easy to scan.

## Bridge to the Python side

The laptop (Python, `app/` in the repo root) connects to this app over Wi-Fi on
port 8765 and controls the drone through it. Message format:
[`DRONE_BRIDGE.md`](../DRONE_BRIDGE.md). How it fits into an app:
[`BRIDGE_INTEGRATION.md`](../BRIDGE_INTEGRATION.md).

- `DroneManagerViewModel` starts the bridge when the app opens and stops it in
  `onCleared`. `pythonConnectionStatus` says whether the laptop is connected;
  bridge events go to the log under the tag `"Python Bridge"`.
- `bridge/BridgeServer.kt` only carries messages: it never calls the DJI SDK.
  It hands commands to `dronecontrollers/DjiCommandHandler.kt`, which flies the
  drone (virtual stick in velocity mode, takeoff/land) and hovers if the laptop
  disconnects or stops sending commands for 1 second.
- When the drone connects, the ViewModel enables virtual stick and starts
  `DjiCameraStreamProvider` (JPEG frames to the laptop) and
  `DjiTelemetryProvider` (battery, position, heading, speed). Both stop when
  the drone disconnects. These live in `DroneManager` with the other drone
  classes.
- `audio/SpeechPlayer.kt` speaks the laptop's `say` alerts out loud.

To test without flying, run `python3 -m scripts.bridge_check --host <phone ip>`
from the repo root on a laptop on the same Wi-Fi.

## Project Structure

```
com.example.dronebuddyapp
├── HomeActivity.kt                 # Single activity, hosts fragments
├── LogFragment.kt                  # Displays the log
├── DroneControllerViewModel.kt     # Shared drone state and connections
└── logcontent
    ├── LogItem.kt                  # Global log object + Status enum
    └── LogRecyclerViewAdapter.kt   # Binds log entries to rows
```

## Conventions

- One activity, many fragments.
- Shared state goes in the ViewModel, not in fragments.
- Important events go in the log, not just Logcat.
- Fragments observe state and send user actions to the ViewModel. They do not talk to drones directly.
