from app.drone.controller import MovementCommand


def test_clamped_limits_each_axis_independently():
    command = MovementCommand(forward=2.0, right=-2.0, up=0.5, yaw=-0.5).clamped()
    assert command.forward == 1.0
    assert command.right == -1.0
    assert command.up == 0.5
    assert command.yaw == -0.5


def test_is_valid_rejects_nan_and_inf():
    assert not MovementCommand(forward=float("nan")).is_valid
    assert not MovementCommand(yaw=float("inf")).is_valid
    assert MovementCommand(forward=0.3).is_valid


def test_is_zero_true_only_for_all_axes_zero():
    assert MovementCommand().is_zero
    assert not MovementCommand(up=0.01).is_zero
