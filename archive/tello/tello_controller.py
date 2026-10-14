import logging
import time
from typing import Optional

import numpy as np
from djitellopy import Tello

from app.drone.controller import DroneController, MovementCommand, Telemetry, Velocity

logger = logging.getLogger("dronebuddy.drone.tello")

# Tello's send_rc_control takes -100..100 "speed" units on each axis (Tello SDK
# spec, not cm/s or m/s) — MAX_RC_SPEED is what a MovementCommand of 1.0 maps to.
MAX_RC_SPEED = 100


class TelloController(DroneController):

    def __init__(self):
        self.drone = Tello()
        self._connected = False

    def connect(self) -> None:
        logger.info("connecting to Tello")
        self.drone.connect()
        self._connected = True
        logger.info("Tello connected battery=%s%%", self.drone.get_battery())

    def disconnect(self) -> None:
        self.drone.end()
        self._connected = False
        logger.info("Tello disconnected")

    def takeoff(self) -> None:
        logger.info("Tello takeoff")
        self.drone.takeoff()

    def land(self) -> None:
        logger.info("Tello land")
        self.drone.land()

    def emergency_stop(self) -> None:
        logger.warning("Tello emergency stop")
        self.drone.emergency()

    def move(self, command: MovementCommand) -> None:
        command = command.clamped()
        self.drone.send_rc_control(
            int(command.right * MAX_RC_SPEED),
            int(command.forward * MAX_RC_SPEED),
            int(command.up * MAX_RC_SPEED),
            int(command.yaw * MAX_RC_SPEED),
        )

    def get_battery(self) -> Optional[int]:
        return self.drone.get_battery()

    def get_telemetry(self) -> Telemetry:
        # Tello has no GPS, so latitude/longitude/heading stay None rather
        # than being reported as 0 — 0 would read as a valid fix to a caller.
        state = self.drone.get_current_state()
        return Telemetry(
            battery=state.get("bat"),
            connected=self._connected,
            altitude=state.get("h"),
            velocity=Velocity(
                x=state.get("vgx", 0),
                y=state.get("vgy", 0),
                z=state.get("vgz", 0),
            ),
            timestamp=time.time(),
        )

    def get_video_frame(self) -> Optional[np.ndarray]:
        frame_read = self.drone.get_frame_read()
        return frame_read.frame if frame_read is not None else None

    def start_video_stream(self) -> None:
        self.drone.streamon()

    def stop_video_stream(self) -> None:
        self.drone.streamoff()

    @property
    def is_connected(self) -> bool:
        return self._connected
