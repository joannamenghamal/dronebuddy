from app.drone.controller import MovementCommand
from app.drone.mock_controller import MockDroneController


def test_lifecycle_tracks_connected_and_airborne_state():
    drone = MockDroneController()
    assert not drone.is_connected

    drone.connect()
    assert drone.is_connected

    drone.takeoff()
    assert drone.is_airborne

    drone.land()
    assert not drone.is_airborne

    drone.disconnect()
    assert not drone.is_connected


def test_move_records_every_command_for_test_assertions():
    drone = MockDroneController()
    command = MovementCommand(forward=0.3, right=-0.2)

    drone.move(command)

    assert drone.commands_received == [command]


def test_get_battery_reflects_set_battery_test_hook():
    drone = MockDroneController(initial_battery=100)
    drone.set_battery(12)

    assert drone.get_battery() == 12
    assert drone.get_telemetry().battery == 12


def test_get_video_frame_returns_a_usable_frame_shape():
    drone = MockDroneController(frame_shape=(240, 320, 3))
    frame = drone.get_video_frame()

    assert frame.shape == (240, 320, 3)
