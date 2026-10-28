"""Runs a recorded clip through the full Visual Buddy pipeline without a window or speech,
then prints a report and saves an annotated copy of the video.

Uses the video's own timestamps as the clock, so activity timing is correct even
when YOLO runs slower than real time on CPU.

Usage (from the project root):
    .venv/Scripts/python.exe tools/analyze_clip.py videos/clip1.mp4
    .venv/Scripts/python.exe tools/analyze_clip.py videos/clip1.mp4 --snapshots 6
"""
import argparse
import os
import sys
from collections import Counter

import cv2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from app.compute_actions import ComputeActions
from app.config import load_config
from app.detection_module import PERSON_LABEL, detect_objects, load_model
from app.drone.controller import HOVER, Telemetry
from app.main import compute_follow_command, draw_overlay
from app.object_locator import ObjectLocator
from app.person_tracker import get_distance_status, get_head_ratio, is_head_cut_off, select_user
from app.safety.safety_manager import SafetyManager
from app.tracking_module import TrackingModule

WEIGHTS_PATH = os.path.join(ROOT_DIR, "app", "yolo11n.pt")
OUTPUT_DIR = os.path.join(ROOT_DIR, "videos", "analyzed")


class VideoClock:
    """Clock driven by the frame number, so 'seconds' are video seconds."""

    def __init__(self, fps):
        self.fps = fps
        self.frame_index = 0

    def __call__(self):
        return self.frame_index / self.fps


def analyze(path, snapshots):
    video = cv2.VideoCapture(path)
    fps = video.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(video.get(3)), int(video.get(4))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{name}_annotated.mp4")
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    snapshot_frames = {int(total_frames * (i + 0.5) / snapshots) for i in range(snapshots)}

    clock = VideoClock(fps)
    model = load_model(WEIGHTS_PATH)
    tracking = TrackingModule(clock)
    actions = ComputeActions(clock=clock)
    locator = ObjectLocator(clock=clock)
    config = load_config()
    safety = SafetyManager(config, clock=clock)

    frames_with_person = 0
    people_per_frame = []
    person_ids = set()
    object_counts = Counter()
    user_id = None
    user_switches = 0
    frames_with_user = 0
    head_ratios = []
    distance_status = Counter()
    timeline = []  # (seconds, kind, text)

    while True:
        success, frame = video.read()
        if not success:
            break

        seconds = clock()
        detections = detect_objects(model, frame)
        people = [d for d in detections if d.label == PERSON_LABEL]

        people_per_frame.append(len(people))
        if people:
            frames_with_person += 1
        for p in people:
            if p.track_id is not None:
                person_ids.add(p.track_id)
        for d in detections:
            if d.label != PERSON_LABEL:
                object_counts[d.label] += 1

        ## Same order as main.py: find the user first, then track everyone else
        user = select_user(people, user_id, width, height)
        if user is not None and user.track_id is not None:
            if user_id is not None and user.track_id != user_id:
                user_switches += 1
            user_id = user.track_id
        if user is not None:
            frames_with_user += 1
            if is_head_cut_off(user.box, height):
                distance_status["HEAD CUT OFF"] += 1
            else:
                head_ratio = get_head_ratio(user.box, height)
                head_ratios.append(head_ratio)
                distance_status[get_distance_status(head_ratio)] += 1

        others = [p for p in people if p is not user]
        events = tracking.update(others, width, height)
        for event in events:
            timeline.append((seconds, "activity", f"person #{event.track_id}: {event.activity}"))
        for alert in actions.compute(events):
            timeline.append((seconds, "SPEAK", alert))
        for _, _, message in locator.locate(detections, width, height):
            timeline.append((seconds, "SPEAK", message))

        ## No drone here - pretend telemetry is live so only the follow logic decides
        safety.note_telemetry(Telemetry(connected=True))
        safety.note_person_visible(user is not None)
        command = compute_follow_command(user, width, height, config)
        decision = safety.decide(command if command is not None else HOVER)

        draw_overlay(frame, detections, user, tracking, decision.command, decision.state)
        cv2.putText(frame, f"t={seconds:5.1f}s", (width - 260, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        writer.write(frame)

        if clock.frame_index in snapshot_frames:
            snap = os.path.join(OUTPUT_DIR, f"{name}_t{seconds:04.1f}s.jpg")
            cv2.imwrite(snap, frame)

        clock.frame_index += 1
        if clock.frame_index % 100 == 0:
            print(f"  ...{clock.frame_index}/{total_frames} frames", flush=True)

    video.release()
    writer.release()

    frame_count = clock.frame_index
    print()
    print(f"===== {path}")
    print(f"{width}x{height} @ {fps:.1f} fps, {frame_count} frames ({frame_count / fps:.1f} s)")
    print(f"Person detected in {frames_with_person}/{frame_count} frames ({100 * frames_with_person / max(frame_count, 1):.0f}%)")
    if people_per_frame:
        print(f"People per frame: max {max(people_per_frame)}, most common {Counter(people_per_frame).most_common(1)[0][0]}")
    print(f"Unique person IDs: {len(person_ids)} {sorted(person_ids)}")
    print(f"User: #{user_id}, visible in {frames_with_user}/{frame_count} frames, switched to another person {user_switches} times")
    if head_ratios:
        ratios = sorted(head_ratios)
        print(f"User head position (0 = top, 1 = bottom): min {ratios[0]:.2f}, median {ratios[len(ratios) // 2]:.2f}, max {ratios[-1]:.2f}")
    print(f"User distance (frames): {dict(distance_status.most_common())}")
    print(f"Other objects (frames seen): {dict(object_counts.most_common(8))}")
    print()
    print("Timeline:")
    for seconds, kind, text in timeline:
        print(f"  {seconds:5.1f}s  {kind:8s} {text}")
    print()
    print(f"Annotated video: {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("clips", nargs="+", help="Video files to analyze")
    parser.add_argument("--snapshots", type=int, default=4, help="Annotated still frames to save per clip")
    args = parser.parse_args()

    for clip in args.clips:
        analyze(clip, args.snapshots)


if __name__ == "__main__":
    main()
