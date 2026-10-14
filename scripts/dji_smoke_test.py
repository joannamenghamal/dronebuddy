"""Staged manual test for the DJI Mini 3 bridge, run once before trusting
app/main.py's autonomous follow-me loop on real hardware. Each flight-
affecting stage (takeoff, move, land) requires a typed "y" confirmation -
nothing happens automatically, since this is meant to be watched with a
hand on the RC the whole time.

Usage: BRIDGE_HOST=<android device ip> python3 -m scripts.dji_smoke_test
"""

import logging
import sys
import time

from app.config import load_config
from app.drone.controller import MovementCommand
from app.drone.dji_controller import DJIController
from app.logging_setup import configure_logging

logger = logging.getLogger("dronebuddy.dji_smoke_test")

TELEMETRY_SAMPLES = 5
TELEMETRY_INTERVAL_S = 1.0
NUDGE_DURATION_S = 1.0


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().lower() == "y"


def require_confirm(prompt: str) -> None:
    if not confirm(prompt):
        print("Aborted by user.")
        sys.exit(1)


def print_telemetry_samples(drone: DJIController) -> None:
    print(f"\n--- sampling telemetry for {TELEMETRY_SAMPLES}s ---")
    for _ in range(TELEMETRY_SAMPLES):
        telemetry = drone.get_telemetry()
        print(
            f"battery={telemetry.battery} connected={telemetry.connected} "
            f"altitude={telemetry.altitude} heading={telemetry.heading}"
        )
        time.sleep(TELEMETRY_INTERVAL_S)


def run_nudge(drone: DJIController, label: str, command: MovementCommand) -> None:
    require_confirm(f"Send '{label}' nudge for {NUDGE_DURATION_S}s?")
    drone.move(command)
    time.sleep(NUDGE_DURATION_S)
    drone.move(MovementCommand())  # explicit hover - never leave a nonzero command outstanding
    print(f"'{label}' nudge sent, returned to hover.")


def main() -> None:
    configure_logging()
    config = load_config()

    print(f"Connecting to DJI bridge at {config.bridge_host}:{config.bridge_port} ...")
    drone = DJIController(config.bridge_host, config.bridge_port)
    drone.connect()
    print("Connected.")

    try:
        print_telemetry_samples(drone)
        require_confirm(
            "\nTelemetry looks sane and the aircraft is already airborne "
            "(taken off manually via the RC)?"
        )

        run_nudge(drone, "up", MovementCommand(up=0.2))
        run_nudge(drone, "forward", MovementCommand(forward=0.2))
        run_nudge(drone, "yaw", MovementCommand(yaw=0.2))

        require_confirm("\nSend land()?")
        drone.land()
        print("land() acknowledged.")

    finally:
        drone.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
