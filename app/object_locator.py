import time

from detection_module import PERSON_LABEL
from person_tracker import describe_position, get_horizontal_error

NEAR_SIZE_RATIO = 0.35       # Box at least this tall or wide (fraction of frame) = object is close
ANNOUNCE_COOLDOWN_S = 10.0   # Don't announce the same kind of object more often than this


class ObjectLocator:
    """Works out where nearby objects are and announces them, e.g. "chair ahead"
    or "bottle on your left". People are handled by the TrackingModule instead."""

    def __init__(self, cooldown_s=ANNOUNCE_COOLDOWN_S, clock=time.monotonic):
        self.cooldown_s = cooldown_s
        self.clock = clock
        self.last_announced = {}  # label -> time it was last announced

    def locate(self, detections, frame_width, frame_height):
        """Returns a list of (label, position, message) for close objects not announced recently."""
        now = self.clock()
        announcements = []

        ## Closest objects first, so the most important one is spoken first
        for detection in sorted(detections, key=lambda d: size_ratio(d.box, frame_width, frame_height), reverse=True):
            if detection.label == PERSON_LABEL:
                continue

            if size_ratio(detection.box, frame_width, frame_height) < NEAR_SIZE_RATIO:
                continue  # Too far away to matter

            ## Track IDs on objects flip around a lot, so the cooldown is per label
            if now - self.last_announced.get(detection.label, float("-inf")) < self.cooldown_s:
                continue

            self.last_announced[detection.label] = now
            position = describe_position(get_horizontal_error(detection.box, frame_width))
            announcements.append((detection.label, position, f"{detection.label} {position}"))

        return announcements


def size_ratio(box, frame_width, frame_height):
    """How much of the frame the object fills: the larger of its height and width fractions."""
    x1, y1, x2, y2 = box
    return max((y2 - y1) / frame_height, (x2 - x1) / frame_width)
