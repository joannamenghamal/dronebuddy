from app.config import Config
from app.control.follow_controller import get_drone_action, get_movement_command

CONFIG = Config(max_forward_speed=0.5, max_lateral_speed=0.4)


def test_too_far_and_centered_moves_forward_only():
    command = get_movement_command("CENTER", "TOO FAR", CONFIG)
    assert command.forward == 0.5
    assert command.right == 0.0


def test_too_close_and_left_backs_away_and_corrects():
    command = get_movement_command("LEFT", "TOO CLOSE", CONFIG)
    assert command.forward == -0.5
    assert command.right == -0.4


def test_good_distance_and_right_only_corrects_laterally():
    command = get_movement_command("RIGHT", "GOOD DISTANCE", CONFIG)
    assert command.forward == 0.0
    assert command.right == 0.4


def test_good_distance_and_centered_is_a_hover_command():
    command = get_movement_command("CENTER", "GOOD DISTANCE", CONFIG)
    assert command.is_zero


def test_command_direction_matches_display_action_label():
    # get_drone_action's string and get_movement_command's vector should never
    # disagree on which way the drone moves - that would be silently confusing
    # to a human watching the on-screen overlay while it flies.
    action = get_drone_action("LEFT", "TOO FAR")
    command = get_movement_command("LEFT", "TOO FAR", CONFIG)
    assert action == "MOVE LEFT + FORWARD"
    assert command.right < 0 and command.forward > 0
