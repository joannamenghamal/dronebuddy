import argparse
import logging

import cv2

from app.audio_output import AudioOutput
from app.compute_actions import ComputeActions
from app.config import load_config
from app.control.follow_controller import describe_command, get_movement_command
from app.detection_module import PERSON_LABEL, detect_objects, load_model
from app.drone.controller import HOVER, DroneController
from app.drone.mock_controller import MockDroneController
from app.logging_setup import configure_logging
from app.object_locator import ObjectLocator
from app.person_tracker import (
    TARGET_HEAD_RATIO,
    get_direction,
    get_distance_status,
    get_head_ratio,
    get_horizontal_error,
    is_head_cut_off,
    select_user,
)
from app.safety.safety_manager import SafetyAction, SafetyManager, SafetyState
from app.session_logger import SessionLogger
from app.tracking_module import TrackingModule
from app.webcam_source import WebcamSource

logger = logging.getLogger("dronebuddy.main")

WEIGHTS_PATH = "yolo11n.pt"
WINDOW_NAME = "Visual Buddy"

BOX_COLOR = (0, 255, 0)
USER_COLOR = (0, 0, 255)
TEXT_COLOR = (0, 255, 0)
ALERT_COLOR = (0, 0, 255)
LABEL_TEXT_COLOR = (0, 0, 0)
HUD_BACKGROUND = (0, 0, 0)


def build_drone(platform: str, source=None) -> DroneController:
    config = load_config()
    if platform == "mock":
        ## Pretend drone uses the laptop camera, or a recorded clip if --source is given
        return MockDroneController(camera=WebcamSource(config.camera_index if source is None else source))
    if platform == "dji":
        from app.drone.dji_controller import DJIController

        return DJIController(config.bridge_host, config.bridge_port)
    raise ValueError(f"unknown drone platform: {platform!r}")


def run(platform: str, source=None, muted=False):
    config = load_config()
    model = load_model(WEIGHTS_PATH)
    safety = SafetyManager(config)

    tracking = TrackingModule()
    actions = ComputeActions()
    locator = ObjectLocator()
    audio = AudioOutput(muted=muted)
    session_log = SessionLogger()

    drone = build_drone(platform, source)
    drone.connect()
    drone.start_video_stream()

    user_id = None

    session_log.log("session_start", platform=platform, source=source)
    audio.say("Visual Buddy ready")

    try:
        while True:
            frame = drone.get_video_frame()

            if frame is None:
                logger.warning("no frame available from %s", platform)
                break

            telemetry = drone.get_telemetry()
            safety.note_telemetry(telemetry)

            frame_height, frame_width = frame.shape[:2]

            ## Detection Module: every object in the frame, with ByteTrack IDs
            detections = detect_objects(model, frame)
            people = [d for d in detections if d.label == PERSON_LABEL]

            ## The user is the person kept at the bottom-middle of the frame;
            ## stay locked on the same track ID while they're visible
            user = select_user(people, user_id, frame_width, frame_height)
            if user is not None and user.track_id is not None:
                user_id = user.track_id

            ## Tracking Module -> Compute Actions -> Audio Output (other people only -
            ## the user doesn't need to be told about themselves)
            others = [p for p in people if p is not user]
            events = tracking.update(others, frame_width, frame_height)
            for event in events:
                session_log.log("activity", track_id=event.track_id, activity=event.activity,
                                horizontal_error=round(event.horizontal_error, 2),
                                height_ratio=round(event.height_ratio, 2))

            for alert in actions.compute(events):
                session_log.log("person_alert", message=alert.text, priority=alert.priority.name)
                audio.say(alert.text, alert.priority, alert.pan)

            ## Object Locator -> Audio Output: objects in the user's path ("chair ahead on your left")
            for label, position, message, pan in locator.locate(detections, user, frame_width, frame_height):
                session_log.log("object_alert", label=label, position=position)
                audio.say(message, pan=pan)

            ## Drone follow: keep the user at the bottom-middle of the frame.
            ## Every command goes through the safety manager before it can reach the drone
            safety.note_person_visible(user is not None)
            command = compute_follow_command(user, frame_width, frame_height, config)
            decision = safety.decide(command if command is not None else HOVER)
            apply_safety_decision(drone, safety, decision)

            draw_overlay(frame, detections, user, tracking, decision.command, decision.state)
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1)
            ## 'q' ends the session, SPACE triggers the emergency stop
            if key == ord("q"):
                break
            if key == ord(" ") and safety.evaluate() != SafetyState.EMERGENCY_STOP:
                safety.trigger_emergency_stop()
                session_log.log("emergency_stop")
                audio.say("Emergency stop")
    finally:
        ## Release camera, close windows, save the log and confirm to the user
        drone.stop_video_stream()
        drone.disconnect()
        cv2.destroyAllWindows()

        log_path = session_log.close()
        logger.info("session log saved to %s", log_path)

        audio.say("Session ended")
        audio.close()


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


def compute_follow_command(user, frame_width, frame_height, config):
    """Movement command that keeps the user at the bottom-middle of the frame,
    or None if the user isn't visible."""
    if user is None:
        return None

    return get_movement_command(
        get_horizontal_error(user.box, frame_width),
        get_head_ratio(user.box, frame_height),
        config,
        head_cut_off=is_head_cut_off(user.box, frame_height),
    )


def draw_overlay(frame, detections, user, tracking, command, safety_state):
    frame_height, frame_width = frame.shape[:2]

    ## Guide mark: where the user's head should be (center, TARGET_HEAD_RATIO down the frame)
    guide_y = int(frame_height * TARGET_HEAD_RATIO)
    cv2.line(frame, (int(frame_width * 0.45), guide_y), (int(frame_width * 0.55), guide_y), USER_COLOR, 2)

    for detection in detections:
        is_user = user is not None and detection is user

        ## One label per box, e.g. "person #2 APPROACHING" or "USER #1"
        if is_user:
            label = "USER" + (f" #{detection.track_id}" if detection.track_id is not None else "")
        else:
            label = detection.label
            if detection.track_id is not None:
                label += f" #{detection.track_id}"
                activity = tracking.activity_of(detection.track_id)
                if activity:
                    label += f" {activity}"

        draw_box(frame, detection.box, label, USER_COLOR if is_user else BOX_COLOR)

    ## Status panel in the top-left corner
    lines = []
    if user is not None:
        horizontal_error = get_horizontal_error(user.box, frame_width)
        head_ratio = get_head_ratio(user.box, frame_height)

        lines.append((f"User: {get_direction(horizontal_error)}", TEXT_COLOR))
        if is_head_cut_off(user.box, frame_height):
            lines.append(("Distance: UNKNOWN (head cut off)", ALERT_COLOR))
        else:
            lines.append((f"Distance: {get_distance_status(head_ratio)} (head at {head_ratio:.2f})", TEXT_COLOR))
    else:
        lines.append(("User not in view", ALERT_COLOR))

    lines.append((f"Command: {describe_command(command)}", TEXT_COLOR))
    lines.append((f"Safety: {safety_state.value}",
                  TEXT_COLOR if safety_state == SafetyState.NOMINAL else ALERT_COLOR))

    draw_panel(frame, lines, (20, 20))


def draw_box(frame, box, label, color):
    x1, y1, x2, y2 = (int(v) for v in box)

    ## Draw bounding box around the object
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    ## Label on a filled tag in the box color so it stays readable on any background
    font_scale = 0.6
    (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
    tag_top = max(y1 - text_height - baseline - 4, 0)
    cv2.rectangle(frame, (x1, tag_top), (x1 + text_width + 6, tag_top + text_height + baseline + 4), color, -1)
    draw_text(frame, label, (x1 + 3, tag_top + text_height + 2), font_scale=font_scale, color=LABEL_TEXT_COLOR)


def draw_panel(frame, lines, origin, font_scale=0.8):
    """Draws lines of (text, color) on a dark semi-transparent panel."""
    line_height = int(40 * font_scale)
    width = max(cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0][0] for text, _ in lines)
    x, y = origin

    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + width + 20, y + line_height * len(lines) + 10), HUD_BACKGROUND, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)

    for i, (text, color) in enumerate(lines):
        draw_text(frame, text, (x + 10, y + line_height * (i + 1)), font_scale=font_scale, color=color)


def draw_text(frame, text, position, font_scale=1.0, color=TEXT_COLOR):
    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        2
    )


def parse_source(source):
    ## A plain number means a local camera, anything else is a file path / stream URL
    if source is None or not source.isdigit():
        return source
    return int(source)


def parse_args():
    parser = argparse.ArgumentParser(description="DroneBuddy Visual Buddy: follow the user and announce what's around them")
    parser.add_argument(
        "--drone",
        choices=["mock", "dji"],
        default=load_config().drone_platform,
        help="Drone backend to drive (default: $DRONE_PLATFORM or 'mock'). "
        "Tello support is archived — see archive/tello/README.md.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="--drone mock only: camera index (e.g. 0), path to a recorded DJI clip, "
        "or a stream URL. Default: $CAMERA_INDEX or 0",
    )
    parser.add_argument(
        "--mute",
        action="store_true",
        help="Log spoken alerts instead of saying them out loud.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    configure_logging()
    args = parse_args()
    run(args.drone, parse_source(args.source), args.mute)
