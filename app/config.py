import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Config:
    drone_platform: str = os.environ.get("DRONE_PLATFORM", "mock")
    bridge_host: str = os.environ.get("BRIDGE_HOST", "127.0.0.1")
    bridge_port: int = _int_env("BRIDGE_PORT", 8765)
    camera_index: int = _int_env("CAMERA_INDEX", 0)

    # Fractions of each platform's own max speed (see MovementCommand) —
    # kept low by default because this drives an autonomous system.
    max_forward_speed: float = _float_env("MAX_FORWARD_SPEED", 0.3)
    max_lateral_speed: float = _float_env("MAX_LATERAL_SPEED", 0.3)
    max_vertical_speed: float = _float_env("MAX_VERTICAL_SPEED", 0.2)
    max_yaw_rate: float = _float_env("MAX_YAW_RATE", 0.3)

    target_distance_px: int = _int_env("TARGET_DISTANCE", 450)

    min_battery_percent: int = _int_env("MIN_BATTERY_PERCENT", 20)
    stale_command_timeout_s: float = _float_env("STALE_COMMAND_TIMEOUT_S", 1.0)
    connection_loss_timeout_s: float = _float_env("CONNECTION_LOSS_TIMEOUT_S", 3.0)
    lost_person_timeout_s: float = _float_env("LOST_PERSON_TIMEOUT_S", 2.0)


def load_config() -> Config:
    return Config()
