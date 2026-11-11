import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Velocity:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Telemetry:
    """Snapshot of aircraft state. Fields the platform can't provide (e.g. GPS
    on a Tello) stay None rather than being faked, so safety logic can tell
    'unsupported' apart from 'zero'."""

    battery: Optional[int] = None
    connected: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    heading: Optional[float] = None
    velocity: Velocity = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.velocity is None:
            self.velocity = Velocity()


@dataclass
class MovementCommand:
    """Desired body-frame velocity, normalized to [-1.0, 1.0] as a fraction of
    the platform's configured max speed for that axis. Normalizing here (instead
    of using drone-specific units like cm/s or DJI's stick percentages) is what
    lets the follow-me controller stay platform-agnostic — each DroneController
    implementation is responsible for scaling into whatever units its own
    flight-control API expects."""

    forward: float = 0.0
    right: float = 0.0
    up: float = 0.0
    yaw: float = 0.0

    def clamped(self) -> "MovementCommand":
        return MovementCommand(
            forward=max(-1.0, min(1.0, self.forward)),
            right=max(-1.0, min(1.0, self.right)),
            up=max(-1.0, min(1.0, self.up)),
            yaw=max(-1.0, min(1.0, self.yaw)),
        )

    @property
    def is_zero(self) -> bool:
        return self.forward == 0.0 and self.right == 0.0 and self.up == 0.0 and self.yaw == 0.0

    @property
    def is_valid(self) -> bool:
        """NaN/inf can reach here from upstream math (e.g. a division by a
        zero-height bounding box) — reject rather than let it hit send_rc_control
        or a DJI virtual-stick call as undefined behavior."""
        return all(math.isfinite(v) for v in (self.forward, self.right, self.up, self.yaw))


HOVER = MovementCommand()


class DroneController(ABC):
    """Platform-agnostic drone interface. The autonomy/follow-me layer talks
    only to this class — never to djitellopy, the DJI SDK, or any other
    vendor API — so swapping aircraft means swapping the implementation, not
    the pipeline."""

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def takeoff(self) -> None:
        ...

    @abstractmethod
    def land(self) -> None:
        ...

    @abstractmethod
    def emergency_stop(self) -> None:
        """Immediate stop of all autonomous movement. This is not a motor
        cutoff: the DJI bridge forces a hover (see DRONE_BRIDGE.md). Must not
        depend on anything that could itself be in a failed state (e.g. the
        video stream or the command channel)."""
        ...

    @abstractmethod
    def move(self, command: MovementCommand) -> None:
        """Apply a normalized velocity command. Implementations must clamp
        to the platform's configured max speeds before sending to hardware."""
        ...

    @abstractmethod
    def get_battery(self) -> Optional[int]:
        ...

    @abstractmethod
    def get_telemetry(self) -> Telemetry:
        ...

    @abstractmethod
    def get_video_frame(self) -> Optional[np.ndarray]:
        ...

    def start_video_stream(self) -> None:
        """No-op by default — platforms that stream on demand (Tello)
        override this; platforms that always stream (a DJI bridge relaying
        the Android camera feed) can leave it as a no-op."""

    def stop_video_stream(self) -> None:
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        ...
