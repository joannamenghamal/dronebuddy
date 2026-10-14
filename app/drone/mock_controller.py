import logging
import time
from typing import List, Optional

import numpy as np

from app.drone.controller import DroneController, MovementCommand, Telemetry

logger = logging.getLogger("dronebuddy.drone.mock")


class MockDroneController(DroneController):
    """Simulated drone for running YOLO -> tracking -> follow-controller ->
    flight-command end to end without hardware. Records every command it
    receives so tests can assert on what the autonomy layer decided to do."""

    def __init__(self, initial_battery: int = 100, frame_shape=(480, 640, 3)):
        self._connected = False
        self._airborne = False
        self._battery = initial_battery
        self._frame_shape = frame_shape
        self.commands_received: List[MovementCommand] = []

    def connect(self) -> None:
        self._connected = True
        logger.info("mock drone connected battery=%s%%", self._battery)

    def disconnect(self) -> None:
        self._connected = False
        logger.info("mock drone disconnected")

    def takeoff(self) -> None:
        self._airborne = True
        logger.info("mock drone takeoff")

    def land(self) -> None:
        self._airborne = False
        logger.info("mock drone land")

    def emergency_stop(self) -> None:
        self._airborne = False
        logger.warning("mock drone emergency stop")

    def move(self, command: MovementCommand) -> None:
        self.commands_received.append(command.clamped())

    def get_battery(self) -> Optional[int]:
        return self._battery

    def set_battery(self, battery: int) -> None:
        """Test hook — lets safety tests simulate a battery drop."""
        self._battery = battery

    def get_telemetry(self) -> Telemetry:
        return Telemetry(
            battery=self._battery,
            connected=self._connected,
            altitude=0.0,
            heading=0.0,
            timestamp=time.time(),
        )

    def get_video_frame(self) -> Optional[np.ndarray]:
        return np.zeros(self._frame_shape, dtype=np.uint8)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_airborne(self) -> bool:
        return self._airborne
