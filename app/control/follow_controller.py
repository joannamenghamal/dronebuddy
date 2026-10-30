from app.config import Config
from app.drone.controller import MovementCommand
from app.person_tracker import DEAD_ZONE, HEAD_TOLERANCE, TARGET_HEAD_RATIO

## Gains are fractions of the configured max speed per unit of error, so the
## command stays normalized (see MovementCommand) on any platform. Both saturate
## before the error does: yaw at 3/4 of the way to the frame edge, forward at
## half a frame of head-position error.
YAW_GAIN = 4 / 3      # x config.max_yaw_rate per unit of horizontal error (-1..1)
FORWARD_GAIN = 2.0    # x config.max_forward_speed per unit of head-position error


## Turns the user's position into a velocity command that keeps them at the bottom-middle
## of the frame. Speed is proportional to how far off we are: small error -> gentle correction.
def get_movement_command(horizontal_error, head_ratio, config: Config, head_cut_off=False) -> MovementCommand:
    command = MovementCommand()

    ## User off-center - turn toward them instead of sliding sideways,
    ## which keeps them in frame much better
    if abs(horizontal_error) > DEAD_ZONE:
        command.yaw = config.max_yaw_rate * _unit_clamp(YAW_GAIN * horizontal_error)

    ## Can't see the top of the head - no distance estimate, so only turn
    if head_cut_off:
        return command

    ## Head high in frame (user walked ahead) -> fly forward,
    ## head low (drone too close, user nearly underneath) -> back away
    distance_error = TARGET_HEAD_RATIO - head_ratio
    if abs(distance_error) > HEAD_TOLERANCE:
        command.forward = config.max_forward_speed * _unit_clamp(FORWARD_GAIN * distance_error)

    ## Altitude is left alone for now - the person's box spans their whole body,
    ## so its vertical position isn't a reliable "go up / go down" signal

    return command


def describe_command(command: MovementCommand) -> str:
    """Short on-screen / log form of a command, e.g. "fwd +0.20  yaw -0.15"."""
    if command.is_zero:
        return "HOVER"
    return f"fwd {command.forward:+.2f}  yaw {command.yaw:+.2f}"


def _unit_clamp(value):
    return max(-1.0, min(1.0, value))
