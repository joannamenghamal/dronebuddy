"""YOLO -> tracker -> follow controller -> mock drone, without a physical
drone or a real camera. YOLO itself is substituted with fixed bounding boxes
(deterministic, fast, no model weights required) - person_tracker and
follow_controller are the real production code under test."""

from app.config import Config
from app.control.follow_controller import get_movement_command
from app.drone.mock_controller import MockDroneController
from app.person_tracker import get_head_ratio, get_horizontal_error, is_head_cut_off
from app.safety.safety_manager import SafetyAction, SafetyManager, SafetyState

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



class CountingDrone(MockDroneController):
    def __init__(self, fail_land_times=0):
        super().__init__()
        self.land_calls = 0
        self.emergency_stops = 0
        self._fail_land_times = fail_land_times

    def land(self):
        self.land_calls += 1
        if self.land_calls <= self._fail_land_times:
            raise RuntimeError("simulated land rejection")
        super().land()

    def emergency_stop(self):
        self.emergency_stops += 1
        super().emergency_stop()


def run_frames_without_user(drone, safety, clock, seconds, landing=False, frame_s=0.1):
    """Steps the loop the way app/main.py does while the user is out of view."""
    from app.main import apply_safety_decision

    decisions = []
    for _ in range(round(seconds / frame_s)):
        clock["t"] += frame_s
        safety.note_telemetry(drone.get_telemetry())
        decision = safety.decide(get_movement_command(0.0, 0.1, CONFIG))
        landing = apply_safety_decision(drone, safety, decision, landing)
        decisions.append(decision)
    return decisions, landing


def test_person_lost_hovers_then_lands_once_after_land_timeout():
    from app.main import apply_safety_decision

    drone = CountingDrone()
    drone.connect()
    clock = {"t": 0.0}
    safety = SafetyManager(CONFIG, clock=lambda: clock["t"])
    run_one_frame(drone, safety, (270, 400, 370, 480))

    decisions, landing = run_frames_without_user(drone, safety, clock, CONFIG.lost_person_land_timeout_s - 0.5)
    assert not landing
    assert decisions[-1].state == SafetyState.LOST_PERSON
    assert drone.land_calls == 0

    decisions, landing = run_frames_without_user(drone, safety, clock, 1.0)
    assert landing
    assert decisions[-1].state == SafetyState.LOST_PERSON_LAND
    assert drone.land_calls == 1

    # The user walks back into view: no movement goes out while landing.
    sent_before = len(drone.commands_received)
    safety.note_person_visible(True)
    decision = safety.decide(get_movement_command(0.3, 0.1, CONFIG))
    assert decision.action == SafetyAction.EXECUTE
    assert apply_safety_decision(drone, safety, decision, landing)
    assert len(drone.commands_received) == sent_before

    # Emergency stop still gets through.
    safety.trigger_emergency_stop()
    apply_safety_decision(drone, safety, safety.decide(get_movement_command(0.0, 0.1, CONFIG)), landing)
    assert drone.emergency_stops == 1


def test_failed_land_request_is_retried_next_frame():
    drone = CountingDrone(fail_land_times=1)
    drone.connect()
    clock = {"t": 0.0}
    safety = SafetyManager(CONFIG, clock=lambda: clock["t"])
    run_one_frame(drone, safety, (270, 400, 370, 480))

    _, landing = run_frames_without_user(drone, safety, clock, CONFIG.lost_person_land_timeout_s + 0.25)
    assert landing
    assert drone.land_calls == 2


class LateFrameDrone(MockDroneController):
    """Like the DJI bridge: no frame until the feed has started."""

    def __init__(self, frames_before_video):
        super().__init__()
        self._polls_left = frames_before_video

    def get_video_frame(self):
        if self._polls_left > 0:
            self._polls_left -= 1
            return None
        return super().get_video_frame()


def test_wait_for_frame_waits_for_a_late_feed():
    from app.main import wait_for_frame

    clock = {"t": 0.0}
    sleep = lambda s: clock.__setitem__("t", clock["t"] + s)
    frame = wait_for_frame(LateFrameDrone(5), 10.0, clock=lambda: clock["t"], sleep=sleep)
    assert frame is not None


def test_wait_for_frame_gives_up_after_timeout():
    from app.main import wait_for_frame

    clock = {"t": 0.0}
    sleep = lambda s: clock.__setitem__("t", clock["t"] + s)
    assert wait_for_frame(LateFrameDrone(10_000), 1.0, clock=lambda: clock["t"], sleep=sleep) is None
    assert clock["t"] >= 1.0


def test_wait_for_frame_without_timeout_checks_once():
    from app.main import wait_for_frame

    assert wait_for_frame(LateFrameDrone(1), 0.0, sleep=lambda s: None) is None
