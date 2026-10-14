import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.drone.controller import HOVER, MovementCommand
from tello_controller import TelloController

tello = TelloController()
airborne = False

try:
    # Connect
    tello.connect()

    # Safety check
    battery = tello.get_battery()

    if battery < 30:
        print(f"Battery too low for flight test: {battery}%")
        raise SystemExit

    print(f"Battery: {battery}%")
    print("Starting flight test in 3 seconds...")
    time.sleep(3)

    # Take off
    tello.takeoff()
    airborne = True

    # Let the drone stabilize
    time.sleep(3)

    # Hover
    tello.move(HOVER)
    time.sleep(2)

    # Move LEFT for 1 second, then hover
    tello.move(MovementCommand(right=-0.3))
    time.sleep(1)
    tello.move(HOVER)
    time.sleep(2)

    # Land
    tello.land()
    airborne = False

finally:
    # If something fails while airborne, attempt to land
    if airborne:
        print("Safety landing...")
        try:
            tello.land()
        except Exception as e:
            print(f"Could not automatically land: {e}")

    tello.disconnect()
