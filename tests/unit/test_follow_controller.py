from app.config import Config
from app.control.follow_controller import describe_command, get_movement_command
from app.person_tracker import TARGET_HEAD_RATIO

CONFIG = Config(max_forward_speed=0.5, max_yaw_rate=0.4)


def test_user_centered_at_target_head_position_is_a_hover_command():
    command = get_movement_command(0.0, TARGET_HEAD_RATIO, CONFIG)
    assert command.is_zero
    assert describe_command(command) == "HOVER"


def test_follow_keeps_head_at_target_position():
    # Values measured in our DJI clip: natural framing, user walked ahead, drone too close
    assert get_movement_command(0.0, 0.41, CONFIG).is_zero
    assert get_movement_command(0.0, 0.15, CONFIG).forward > 0
    assert get_movement_command(0.0, 0.87, CONFIG).forward < 0


def test_off_center_user_turns_toward_them_instead_of_sliding():
    left = get_movement_command(-0.5, TARGET_HEAD_RATIO, CONFIG)
    right = get_movement_command(0.5, TARGET_HEAD_RATIO, CONFIG)
    assert left.yaw < 0 < right.yaw
    assert left.right == 0.0 and right.right == 0.0


def test_command_never_exceeds_configured_max_speeds():
    # User at the far right edge with their head at the very bottom of the frame
    command = get_movement_command(1.0, 1.0, CONFIG)
    assert command.yaw == 0.4
    assert command.forward == -0.5


def test_small_errors_give_gentle_corrections():
    gentle = get_movement_command(0.2, 0.25, CONFIG)
    strong = get_movement_command(0.6, 0.05, CONFIG)
    assert 0 < gentle.yaw < strong.yaw
    assert 0 < gentle.forward < strong.forward


def test_head_cut_off_only_turns():
    command = get_movement_command(0.5, 0.0, CONFIG, head_cut_off=True)
    assert command.forward == 0
    assert command.yaw > 0
