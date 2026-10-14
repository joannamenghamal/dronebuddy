"""YOLO -> tracker -> follow controller -> mock drone, without a physical
drone or a real camera. YOLO itself is substituted with fixed bounding boxes
(deterministic, fast, no model weights required) - person_tracker and
follow_controller are the real production code under test."""

from app.config import Config
from app.control.follow_controller import get_movement_command
from app.drone.mock_controller import MockDroneController
from app.person_tracker import get_direction, get_distance_status
from app.safety.safety_manager import SafetyAction, SafetyManager

FRAME_WIDTH = 640
CONFIG = Config(max_forward_speed=0.4, max_lateral_speed=0.3)


def run_one_frame(drone, safety, box):
    telemetry = drone.get_telemetry()
    safety.note_telemetry(telemetry)
    safety.note_person_visible(True)

    direction = get_direction(box, FRAME_WIDTH)
    distance_status = get_distance_status(box)
    command = get_movement_command(direction, distance_status, CONFIG)

    decision = safety.decide(command)
    if decision.action == SafetyAction.EXECUTE:
        drone.move(decision.command)
        safety.note_command_issued()
    else:
        drone.move(decision.command)

    return decision


def test_person_far_and_left_of_center_moves_forward_and_left():
    drone = MockDroneController()
    drone.connect()
    safety = SafetyManager(CONFIG)

    # Small, left-of-center box -> far away and off to the left.
    box = (50, 100, 150, 300)

    decision = run_one_frame(drone, safety, box)

    assert decision.action == SafetyAction.EXECUTE
    assert drone.commands_received[-1].forward > 0
    assert drone.commands_received[-1].right < 0


def test_person_close_and_centered_backs_away_with_no_lateral_drift():
    drone = MockDroneController()
    drone.connect()
    safety = SafetyManager(CONFIG)

    # Tall, centered box -> too close, dead ahead.
    box = (270, 20, 370, 700)

    decision = run_one_frame(drone, safety, box)

    assert decision.action == SafetyAction.EXECUTE
    assert drone.commands_received[-1].forward < 0
    assert drone.commands_received[-1].right == 0


def test_person_lost_after_timeout_falls_back_to_hover():
    drone = MockDroneController()
    drone.connect()

    clock = {"t": 0.0}
    safety = SafetyManager(CONFIG, clock=lambda: clock["t"])

    box = (270, 20, 370, 700)
    run_one_frame(drone, safety, box)

    # Person disappears - no further note_person_visible(True) calls - and
    # enough time passes to cross the configured lost-person timeout.
    clock["t"] += CONFIG.lost_person_timeout_s + 0.1
    safety.note_telemetry(drone.get_telemetry())

    decision = safety.decide(get_movement_command("CENTER", "TOO FAR", CONFIG))

    assert decision.action == SafetyAction.HOVER
    assert decision.command.is_zero
