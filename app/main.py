import argparse
import logging

import cv2

from app.config import load_config
from app.control.follow_controller import get_drone_action, get_movement_command
from app.drone.controller import HOVER, DroneController
from app.drone.mock_controller import MockDroneController
from app.logging_setup import configure_logging
from app.person_detector import PERSON_LABEL, detect_objects, load_model
from app.person_tracker import get_direction, get_distance_status
from app.safety.safety_manager import SafetyAction, SafetyManager
from app.webcam_source import WebcamSource

logger = logging.getLogger("dronebuddy.main")

WEIGHTS_PATH = "yolo11n.pt"
WINDOW_NAME = "YOLO Detection"


def build_drone(platform: str) -> DroneController:
    config = load_config()
    if platform == "mock":
        ## Pretend drone uses the laptop camera
        return MockDroneController(camera=WebcamSource(config.camera_index))
    if platform == "dji":
        from app.drone.dji_controller import DJIController

        return DJIController(config.bridge_host, config.bridge_port)
    raise ValueError(f"unknown drone platform: {platform!r}")


def run(platform: str):
    config = load_config()
    model = load_model(WEIGHTS_PATH)
    safety = SafetyManager(config)

    drone = build_drone(platform)
    drone.connect()
    drone.start_video_stream()

    try:
        while True:
            frame = drone.get_video_frame()

            if frame is None:
                logger.warning("no frame available from %s", platform)
                break

            telemetry = drone.get_telemetry()
            safety.note_telemetry(telemetry)

            frame_width = frame.shape[1]
            person_visible = False

            for label, box in detect_objects(model, frame):
                draw_box(frame, box, label)

                ## Following only makes sense for a person - every other
                ## object just gets labeled and otherwise ignored.
                if label != PERSON_LABEL:
                    continue

                person_visible = True

                direction = get_direction(box, frame_width)
                distance_status = get_distance_status(box)
                action = get_drone_action(direction, distance_status)
                desired_command = get_movement_command(direction, distance_status, config)

                draw_person_status(frame, direction, distance_status, action)
                log_detection(box, direction, distance_status, action)

            safety.note_person_visible(person_visible)

            command = desired_command if person_visible else HOVER
            decision = safety.decide(command)
            apply_safety_decision(drone, safety, decision)

            ## Display the frame
            cv2.imshow(WINDOW_NAME, frame)

            ## Exit when 'q' is pressed
            if cv2.waitKey(1) == ord("q"):
                break
    finally:
        ## Release camera and close OpenCV windows
        drone.stop_video_stream()
        drone.disconnect()
        cv2.destroyAllWindows()


def apply_safety_decision(drone: DroneController, safety: SafetyManager, decision) -> None:
    if decision.state.name != "NOMINAL":
        logger.info("safety state=%s action=%s", decision.state.value, decision.action.value)

    if decision.action == SafetyAction.EXECUTE:
        drone.move(decision.command)
        safety.note_command_issued()
    elif decision.action == SafetyAction.HOVER:
        drone.move(decision.command)
    elif decision.action == SafetyAction.LAND:
        drone.land()
    elif decision.action == SafetyAction.EMERGENCY_STOP:
        drone.emergency_stop()


def draw_box(frame, box, label):
    x1, y1, x2, y2 = box

    ## Draw bounding box + class label around every detected object
    cv2.rectangle(
        frame,
        (int(x1), int(y1)),
        (int(x2), int(y2)),
        (0, 255, 0),
        2
    )

    draw_text(frame, label, (int(x1), int(y1) - 10), font_scale=0.6)


def draw_person_status(frame, direction, distance_status, action):
    ## Display direction
    draw_text(frame, f"Direction: {direction}", (30, 50))

    ## Display distance
    draw_text(frame, f"Distance: {distance_status}", (30, 90))

    ## Display drone action
    draw_text(frame, f"Action: {action}", (30, 130), font_scale=0.8)


def draw_text(frame, text, position, font_scale=1.0):
    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (0, 255, 0),
        2
    )


def log_detection(box, direction, distance_status, action):
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    logger.info(
        "person detected box=%s center=(%.1f, %.1f) direction=%s distance=%s action=%s",
        box, center_x, center_y, direction, distance_status, action,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="DroneBuddy follow-me")
    parser.add_argument(
        "--drone",
        choices=["mock", "dji"],
        default=load_config().drone_platform,
        help="Drone backend to drive (default: $DRONE_PLATFORM or 'mock'). "
        "Tello support is archived — see archive/tello/README.md.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    configure_logging()
    args = parse_args()
    run(args.drone)
