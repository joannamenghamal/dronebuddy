from dataclasses import dataclass

from person_tracker import DEAD_ZONE, HEAD_TOLERANCE, TARGET_HEAD_RATIO

## Units match DJI MSDK v5 Virtual Stick in VELOCITY mode, body frame:
## forward/right/up in m/s, yaw in deg/s (+ = clockwise)
YAW_GAIN = 40.0      # deg/s of yaw per unit of horizontal error (-1..1)
FORWARD_GAIN = 2.0   # m/s of forward speed per unit of head-position error


@dataclass
class VelocityCommand:
    forward: float = 0.0  # m/s, + = forward, - = backward
    right: float = 0.0    # m/s, + = right, - = left
    up: float = 0.0       # m/s, + = up, - = down
    yaw: float = 0.0      # deg/s, + = turn right (clockwise)

    def is_hover(self):
        return self.forward == 0 and self.right == 0 and self.up == 0 and self.yaw == 0

    def __str__(self):
        if self.is_hover():
            return "HOVER"
        return f"fwd {self.forward:+.2f} m/s  yaw {self.yaw:+.0f} deg/s"


## Turns the user's position into a velocity command that keeps them at the bottom-middle
## of the frame. Speed is proportional to how far off we are: small error -> gentle correction.
def get_drone_action(horizontal_error, head_ratio, head_cut_off=False):
    command = VelocityCommand()

    ## User off-center - turn toward them instead of sliding sideways,
    ## which keeps them in frame much better
    if abs(horizontal_error) > DEAD_ZONE:
        command.yaw = YAW_GAIN * horizontal_error

    ## Can't see the top of the head - no distance estimate, so only turn
    if head_cut_off:
        return command

    ## Head high in frame (user walked ahead) -> fly forward,
    ## head low (drone too close, user nearly underneath) -> back away
    distance_error = TARGET_HEAD_RATIO - head_ratio
    if abs(distance_error) > HEAD_TOLERANCE:
        command.forward = FORWARD_GAIN * distance_error

    ## Altitude is left alone for now - the person's box spans their whole body,
    ## so its vertical position isn't a reliable "go up / go down" signal

    return command
