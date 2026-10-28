"""YOLO -> tracker -> follow controller -> mock drone, without a physical
drone or a real camera. YOLO itself is substituted with fixed bounding boxes
(deterministic, fast, no model weights required) - person_tracker and
follow_controller are the real production code under test."""

from app.config import Config
from app.control.follow_controller import get_movement_command
from app.drone.mock_controller import MockDroneController
from app.person_tracker import get_head_ratio, get_horizontal_error, is_head_cut_off
from app.safety.safety_manager import SafetyAction, SafetyManager

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CONFIG = Config(max_forward_speed=0.4, max_yaw_rate=0.3)


def run_one_frame(drone, safety, box):
    telemetry = drone.get_telemetry()
    safety.note_telemetry(telemetry)
    safety.note_person_visible(True)

    command = get_movement_command(
        get_horizontal_error(box, FRAME_WIDTH),
        get_head_ratio(box, FRAME_HEIGHT),
        CONFIG,
        head_cut_off=is_head_cut_off(box, FRAME_HEIGHT),
    )

    decision = safety.decide(command)
    if decision.action == SafetyAction.EXECUTE:
        drone.move(decision.command)
        safety.note_command_issued()
    else:
        drone.move(decision.command)

    return decision


def test_user_far_ahead_and_left_of_center_flies_forward_and_turns_left():
    drone = MockDroneController()
    drone.connect()
    safety = SafetyManager(CONFIG)

    # Head high in the frame and off to the left -> user walked ahead and drifted left.
    box = (50, 40, 150, 300)

    decision = run_one_frame(drone, safety, box)

    assert decision.action == SafetyAction.EXECUTE
    assert drone.commands_received[-1].forward > 0
    assert drone.commands_received[-1].yaw < 0


def test_user_nearly_underneath_and_centered_backs_away_without_turning():
    drone = MockDroneController()
    drone.connect()
    safety = SafetyManager(CONFIG)

    # Head low in the frame, centered -> drone too close, user dead ahead.
    box = (270, 400, 370, 480)

    decision = run_one_frame(drone, safety, box)

    assert decision.action == SafetyAction.EXECUTE
    assert drone.commands_received[-1].forward < 0
    assert drone.commands_received[-1].yaw == 0


def test_person_lost_after_timeout_falls_back_to_hover():
    drone = MockDroneController()
    drone.connect()

    clock = {"t": 0.0}
    safety = SafetyManager(CONFIG, clock=lambda: clock["t"])

    box = (270, 400, 370, 480)
    run_one_frame(drone, safety, box)

    # Person disappears - no further note_person_visible(True) calls - and
    # enough time passes to cross the configured lost-person timeout.
    clock["t"] += CONFIG.lost_person_timeout_s + 0.1
    safety.note_telemetry(drone.get_telemetry())

    decision = safety.decide(get_movement_command(0.0, 0.1, CONFIG))

    assert decision.action == SafetyAction.HOVER
    assert decision.command.is_zero
