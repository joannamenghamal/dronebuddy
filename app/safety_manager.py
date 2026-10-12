import time

from control.follow_controller import VelocityCommand

MAX_SPEED = 1.0         # m/s, applies to forward/right/up
MAX_YAW = 30.0          # deg/s
LAND_AFTER_LOST_S = 5.0  # Seconds without a target before we recommend landing


class SafetyManager:
    """Last check on every command before it can reach the drone.

    - Clamps all speeds to safe limits
    - Hovers whenever no person is in view
    - Flags that the drone should land after losing the person for too long
    - Emergency stop latches: once triggered, only hover goes out until reset
    """

    def __init__(self, max_speed=MAX_SPEED, max_yaw=MAX_YAW,
                 land_after_lost_s=LAND_AFTER_LOST_S, clock=time.monotonic):
        self.max_speed = max_speed
        self.max_yaw = max_yaw
        self.land_after_lost_s = land_after_lost_s
        self.clock = clock

        self.emergency_stopped = False
        self.target_seen = False
        self.last_seen = clock()

    def filter(self, command, target_seen):
        """Returns the command that is actually safe to send."""
        self.target_seen = target_seen
        if target_seen:
            self.last_seen = self.clock()

        if self.emergency_stopped or not target_seen or command is None:
            return VelocityCommand()

        return VelocityCommand(
            forward=clamp(command.forward, self.max_speed),
            right=clamp(command.right, self.max_speed),
            up=clamp(command.up, self.max_speed),
            yaw=clamp(command.yaw, self.max_yaw),
        )

    def seconds_since_seen(self):
        return self.clock() - self.last_seen

    def should_land(self):
        return self.seconds_since_seen() > self.land_after_lost_s

    def trigger_emergency_stop(self):
        self.emergency_stopped = True

    def reset_emergency_stop(self):
        self.emergency_stopped = False

    def status(self):
        if self.emergency_stopped:
            return "EMERGENCY STOP"
        if self.should_land():
            return "TARGET LOST - LAND"
        if not self.target_seen:
            return "TARGET LOST - HOVER"
        return "OK"


def clamp(value, limit):
    return max(-limit, min(limit, value))
