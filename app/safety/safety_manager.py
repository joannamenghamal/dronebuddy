import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.config import Config
from app.drone.controller import HOVER, MovementCommand, Telemetry

logger = logging.getLogger("dronebuddy.safety")


class SafetyState(Enum):
    NOMINAL = "NOMINAL"
    LOST_PERSON = "LOST_PERSON"
    LOST_PERSON_LAND = "LOST_PERSON_LAND"
    LOW_BATTERY = "LOW_BATTERY"
    STALE_COMMAND = "STALE_COMMAND"
    CONNECTION_LOST = "CONNECTION_LOST"
    INVALID_COMMAND = "INVALID_COMMAND"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class SafetyAction(Enum):
    EXECUTE = "EXECUTE"
    HOVER = "HOVER"
    LAND = "LAND"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class SafetyDecision:
    state: SafetyState
    action: SafetyAction
    command: MovementCommand


class SafetyManager:
    """Single authority for whether a desired flight command is safe to send.

    Deliberately returns a decision rather than touching a DroneController
    itself — that keeps it unit-testable with fake clocks/telemetry, and
    keeps the choice of *how* to execute LAND/EMERGENCY_STOP with the caller,
    which already owns the DroneController instance.

    This does not, and must not, replace the aircraft's own firmware
    failsafes (Tello's signal-loss auto-land, DJI's RTH-on-signal-loss). Real
    connection loss can't be mitigated from here — nothing sent from this
    process can reach the aircraft in that case. This class exists to stop
    the autonomy layer from doing anything unsafe with a link that's degraded
    but not fully gone (stale telemetry, stale commands, lost target).
    """

    def __init__(self, config: Config, clock=time.time):
        self._config = config
        self._clock = clock
        self._last_command_at: Optional[float] = None
        self._last_telemetry_at: Optional[float] = None
        self._last_battery: Optional[int] = None
        self._last_person_visible_at: Optional[float] = None
        self._emergency_stopped = False

    def note_command_issued(self) -> None:
        self._last_command_at = self._clock()

    def note_telemetry(self, telemetry: Telemetry) -> None:
        self._last_telemetry_at = self._clock()
        self._last_battery = telemetry.battery

    def note_person_visible(self, visible: bool) -> None:
        if visible:
            self._last_person_visible_at = self._clock()

    def trigger_emergency_stop(self) -> None:
        logger.warning("emergency stop triggered")
        self._emergency_stopped = True

    def reset_emergency_stop(self) -> None:
        """Requires an explicit, separate call — emergency stop must never
        clear itself as a side effect of telemetry or commands resuming."""
        self._emergency_stopped = False

    def evaluate(self) -> SafetyState:
        now = self._clock()

        if self._emergency_stopped:
            return SafetyState.EMERGENCY_STOP

        if (
            self._last_battery is not None
            and self._last_battery <= self._config.min_battery_percent
        ):
            return SafetyState.LOW_BATTERY

        if (
            self._last_telemetry_at is None
            or now - self._last_telemetry_at > self._config.connection_loss_timeout_s
        ):
            return SafetyState.CONNECTION_LOST

        if (
            self._last_command_at is not None
            and now - self._last_command_at > self._config.stale_command_timeout_s
        ):
            return SafetyState.STALE_COMMAND

        if self._last_person_visible_at is not None:
            lost_for = now - self._last_person_visible_at
            if lost_for > self._config.lost_person_land_timeout_s:
                return SafetyState.LOST_PERSON_LAND
            if lost_for > self._config.lost_person_timeout_s:
                return SafetyState.LOST_PERSON

        return SafetyState.NOMINAL

    def decide(self, desired_command: MovementCommand) -> SafetyDecision:
        if not desired_command.is_valid:
            logger.warning("rejecting invalid movement command: %r", desired_command)
            return SafetyDecision(SafetyState.INVALID_COMMAND, SafetyAction.HOVER, HOVER)

        state = self.evaluate()

        if state == SafetyState.EMERGENCY_STOP:
            return SafetyDecision(state, SafetyAction.EMERGENCY_STOP, HOVER)

        if state in (SafetyState.LOW_BATTERY, SafetyState.LOST_PERSON_LAND):
            return SafetyDecision(state, SafetyAction.LAND, HOVER)

        if state in (
            SafetyState.CONNECTION_LOST,
            SafetyState.STALE_COMMAND,
            SafetyState.LOST_PERSON,
        ):
            return SafetyDecision(state, SafetyAction.HOVER, HOVER)

        return SafetyDecision(state, SafetyAction.EXECUTE, desired_command.clamped())
