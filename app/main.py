import argparse

import cv2

from audio_output import AudioOutput
from compute_actions import ComputeActions
from control.follow_controller import get_drone_action
from detection_module import PERSON_LABEL, detect_objects, load_model
from object_locator import ObjectLocator
from person_tracker import (
    TARGET_HEAD_RATIO,
    get_direction,
    get_distance_status,
    get_head_ratio,
    get_horizontal_error,
    is_head_cut_off,
    select_user,
)
from safety_manager import SafetyManager
from session_logger import SessionLogger
from tracking_module import TrackingModule

WEIGHTS_PATH = "yolo11n.pt"
WINDOW_NAME = "Visual Buddy"

BOX_COLOR = (0, 255, 0)
USER_COLOR = (0, 0, 255)
TEXT_COLOR = (0, 255, 0)
ALERT_COLOR = (0, 0, 255)
LABEL_TEXT_COLOR = (0, 0, 0)
HUD_BACKGROUND = (0, 0, 0)


def parse_args():
    parser = argparse.ArgumentParser(description="Detect, track and announce people and objects in a video feed.")
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index (e.g. 0), path to a recorded DJI clip, or a stream URL. Default: 0",
    )
    return parser.parse_args()


def open_source(source):
    ## A plain number means a local camera, anything else is a file path / stream URL
    if source.isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def run(source):
    model = load_model(WEIGHTS_PATH)
    video = open_source(source)

    tracking = TrackingModule()
    actions = ComputeActions()
    locator = ObjectLocator()
    audio = AudioOutput()
    logger = SessionLogger()
    safety = SafetyManager()

    user_id = None

    logger.log("session_start", source=source)
    audio.say("Visual Buddy ready")

    try:
        ## Loop to continuously read frames and perform detection + tracking
        while True:

            success, frame = video.read()  # Read a frame from the video source

            if not success:
                print("No more frames (video ended or source unavailable)")
                break

            frame_height, frame_width = frame.shape[:2]  # Get frame dimensions

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
                logger.log("activity", track_id=event.track_id, activity=event.activity,
                           horizontal_error=round(event.horizontal_error, 2),
                           height_ratio=round(event.height_ratio, 2))

            for alert in actions.compute(events):
                logger.log("person_alert", message=alert)
                audio.say(alert)

            ## Object Locator -> Audio Output (everything that isn't a person)
            for label, position, message in locator.locate(detections, frame_width, frame_height):
                logger.log("object_alert", label=label, position=position)
                audio.say(message)

            ## Drone follow: keep the user at the bottom-middle of the frame
            command = compute_follow_command(user, frame_width, frame_height)

            ## Every command goes through the safety manager before it could reach the drone
            safe_command = safety.filter(command, target_seen=user is not None)

            draw_overlay(frame, detections, user, tracking, safe_command, safety.status())
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1)
            ## 'q' ends the session, SPACE toggles the emergency stop
            if key == ord("q"):
                break
            if key == ord(" "):
                if safety.emergency_stopped:
                    safety.reset_emergency_stop()
                    logger.log("emergency_stop_reset")
                else:
                    safety.trigger_emergency_stop()
                    logger.log("emergency_stop")
                    audio.say("Emergency stop")
    finally:
        ## Release video source, close windows, save the log and confirm to the user
        video.release()
        cv2.destroyAllWindows()

        log_path = logger.close()
        print(f"Session log saved to {log_path}")

        audio.say("Session ended")
        audio.close()


def compute_follow_command(user, frame_width, frame_height):
    """Drone velocity command that keeps the user at the bottom-middle of the frame,
    or None if the user isn't visible."""
    if user is None:
        return None

    return get_drone_action(
        get_horizontal_error(user.box, frame_width),
        get_head_ratio(user.box, frame_height),
        head_cut_off=is_head_cut_off(user.box, frame_height),
    )


def draw_overlay(frame, detections, user, tracking, command, safety_status):
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

    lines.append((f"Command: {command}", TEXT_COLOR))
    lines.append((f"Safety: {safety_status}", TEXT_COLOR if safety_status == "OK" else ALERT_COLOR))

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


if __name__ == "__main__":
    run(parse_args().source)
