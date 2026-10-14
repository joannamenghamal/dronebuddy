from app.config import Config
from app.drone.controller import MovementCommand


## Turns the tracked direction + distance into a single drone command
def get_drone_action(direction, distance_status):

    ## Person is too far away - move closer, correcting left/right on the way
    if distance_status == "TOO FAR":
        if direction == "LEFT":
            return "MOVE LEFT + FORWARD"
        elif direction == "RIGHT":
            return "MOVE RIGHT + FORWARD"
        else:
            return "MOVE FORWARD"

    ## Person is too close - back away, correcting left/right on the way
    elif distance_status == "TOO CLOSE":
        if direction == "LEFT":
            return "MOVE LEFT + BACKWARD"
        elif direction == "RIGHT":
            return "MOVE RIGHT + BACKWARD"
        else:
            return "MOVE BACKWARD"

    ## Distance is good - only correct left/right, or hover if already centered
    else:
        if direction == "LEFT":
            return "MOVE LEFT"
        elif direction == "RIGHT":
            return "MOVE RIGHT"
        else:
            return "HOVER"


def get_movement_command(direction, distance_status, config: Config) -> MovementCommand:
    """Same decision table as get_drone_action, adapted to emit a normalized
    MovementCommand instead of a display string, so it can be handed to any
    DroneController through SafetyManager. Kept as a separate function rather
    than changing get_drone_action's return type, since the string form is
    still used for on-screen/log display."""

    forward = 0.0
    right = 0.0

    if distance_status == "TOO FAR":
        forward = config.max_forward_speed
    elif distance_status == "TOO CLOSE":
        forward = -config.max_forward_speed

    if direction == "LEFT":
        right = -config.max_lateral_speed
    elif direction == "RIGHT":
        right = config.max_lateral_speed

    return MovementCommand(forward=forward, right=right, up=0.0, yaw=0.0)
