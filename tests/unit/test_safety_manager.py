from app.config import Config
from app.drone.controller import MovementCommand, Telemetry
from app.safety.safety_manager import SafetyAction, SafetyManager, SafetyState

CONFIG = Config(
    min_battery_percent=20,
    stale_command_timeout_s=1.0,
    connection_loss_timeout_s=3.0,
    lost_person_timeout_s=2.0,
    lost_person_land_timeout_s=5.0,
)

MOVE = MovementCommand(forward=0.5)


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_manager():
    clock = FakeClock()
    manager = SafetyManager(CONFIG, clock=clock)
    return manager, clock


def test_nominal_flow_executes_command_and_tracks_state():
    manager, clock = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    decision = manager.decide(MOVE)

    assert decision.state == SafetyState.NOMINAL
    assert decision.action == SafetyAction.EXECUTE
    assert decision.command == MOVE.clamped()


def test_no_telemetry_yet_is_treated_as_connection_lost():
    manager, _ = make_manager()

    decision = manager.decide(MOVE)

    assert decision.state == SafetyState.CONNECTION_LOST
    assert decision.action == SafetyAction.HOVER


def test_connection_loss_detected_after_timeout_elapses():
    manager, clock = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    clock.advance(CONFIG.connection_loss_timeout_s + 0.1)

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.CONNECTION_LOST
    assert decision.action == SafetyAction.HOVER


def test_stale_command_detected_after_timeout_elapses():
    manager, clock = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)
    manager.note_command_issued()

    clock.advance(CONFIG.stale_command_timeout_s + 0.1)

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.STALE_COMMAND
    assert decision.action == SafetyAction.HOVER


def test_lost_person_detected_after_timeout_elapses():
    manager, clock = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    clock.advance(CONFIG.lost_person_timeout_s + 0.1)

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.LOST_PERSON
    assert decision.action == SafetyAction.HOVER


def test_lost_person_triggers_land_after_land_timeout():
    manager, clock = make_manager()
    manager.note_person_visible(True)

    clock.advance(CONFIG.lost_person_land_timeout_s + 0.1)
    manager.note_telemetry(Telemetry(battery=80, connected=True))

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.LOST_PERSON_LAND
    assert decision.action == SafetyAction.LAND
    assert decision.command.is_zero


def test_lost_person_still_hovers_just_before_land_timeout():
    manager, clock = make_manager()
    manager.note_person_visible(True)

    clock.advance(CONFIG.lost_person_land_timeout_s - 0.1)
    manager.note_telemetry(Telemetry(battery=80, connected=True))

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.LOST_PERSON
    assert decision.action == SafetyAction.HOVER


def test_low_battery_triggers_land_even_if_otherwise_nominal():
    manager, _ = make_manager()
    manager.note_telemetry(Telemetry(battery=15, connected=True))
    manager.note_person_visible(True)

    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.LOW_BATTERY
    assert decision.action == SafetyAction.LAND


def test_emergency_stop_latches_until_explicitly_reset():
    manager, _ = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    manager.trigger_emergency_stop()
    decision = manager.decide(MOVE)
    assert decision.state == SafetyState.EMERGENCY_STOP
    assert decision.action == SafetyAction.EMERGENCY_STOP

    # Fresh telemetry/commands must not clear it on their own.
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    assert manager.decide(MOVE).state == SafetyState.EMERGENCY_STOP

    manager.reset_emergency_stop()
    assert manager.decide(MOVE).state == SafetyState.NOMINAL


def test_invalid_command_rejected_regardless_of_other_state():
    manager, _ = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    decision = manager.decide(MovementCommand(forward=float("nan")))
    assert decision.state == SafetyState.INVALID_COMMAND
    assert decision.action == SafetyAction.HOVER


def test_executed_command_is_clamped_to_output_limits():
    manager, _ = make_manager()
    manager.note_telemetry(Telemetry(battery=80, connected=True))
    manager.note_person_visible(True)

    decision = manager.decide(MovementCommand(forward=5.0, right=-5.0))
    assert decision.action == SafetyAction.EXECUTE
    assert decision.command.forward == 1.0
    assert decision.command.right == -1.0
