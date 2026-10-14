# Archived: Tello backend

This directory holds the DJI Tello-specific code that was in active use
before the migration to the DJI Mini 3. It is kept for reference (and in
case a Tello is ever useful again for cheap indoor testing of the follow-me
logic) but is **not** wired into `app/main.py`'s `--drone` CLI anymore —
only `mock` and `dji` are active backends now. See
[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Contents

- `tello_controller.py` — the `TelloController(DroneController)` implementation
  that used to live at `app/drone/tello_controller.py`. Unchanged apart from
  its location.
- `camera_test.py` — the pre-abstraction scratch script that drove a Tello
  directly via `djitellopy`, used during early detection/tracking development.
- `test_flight.py` — a manual, real-hardware flight script. Never a pytest
  test; it has module-level side effects (connects to and flies a real Tello)
  and must never be auto-collected.

## Reviving this backend

1. `pip install djitellopy==2.5.0` (removed from the main `requirements.txt`
   since nothing in `app/` imports it anymore).
2. Copy `tello_controller.py` back to `app/drone/tello_controller.py`.
3. In `app/main.py`: re-add the import, the `"tello"` branch in
   `build_drone()`, and `"tello"` to the `--drone` argparse `choices`.
4. `test_flight.py` imports its sibling `tello_controller.py` via a
   `sys.path` insert (see the top of the file) rather than through the `app`
   package, since it's meant to run standalone from here:
   `PYTHONPATH=. python archive/tello/test_flight.py`.
