import time

from app.detection_module import PERSON_LABEL
from app.person_tracker import TARGET_HEAD_RATIO, describe_position, get_horizontal_error

ANNOUNCE_COOLDOWN_S = 10.0  # Don't announce the same kind of object more often than this
PATH_SIDE_WIDTHS = 1.0      # The path = the user's own width plus this many body-widths on each side
NO_USER_PATH = (1 / 3, 2 / 3)  # User not in view: the middle third of the frame is the path
## How far ahead the path reaches: an object counts only if its bottom edge is below this
## line (as a fraction of the frame height). The drone holds the user's head on the same
## line, and with the camera's fixed tilt, height in the frame is distance on the ground:
## on our DJI clips, every object above it was a car parked far across the lot.
PATH_FAR_EDGE = TARGET_HEAD_RATIO
RECENT_S = 2.0              # find(): seen this recently = "is", older = "seen N seconds ago"
REMEMBER_S = 30.0           # find(): forget objects not seen for this long


class ObjectLocator:
    """Warns about objects in the user's path ("chair ahead on your left"), and remembers
    where every object was last seen, to answer "where is my cup?".

    The drone flies behind the user, so "ahead" is higher up the frame than the user,
    and the left of the frame is the user's left. People are handled by the
    TrackingModule instead."""

    def __init__(self, cooldown_s=ANNOUNCE_COOLDOWN_S, clock=time.monotonic):
        self.cooldown_s = cooldown_s
        self.clock = clock
        self.last_announced = {}  # label -> time it was last announced
        self.last_seen = {}       # label -> (time, position words, pan) of the nearest one last seen

    def locate(self, detections, user, frame_width, frame_height):
        """Remembers every object in view, and returns the ones in the user's path that
        weren't announced recently, nearest first, as (label, position, message, pan).
        user: the user's Detection, or None if they're not in view."""
        now = self.clock()
        objects = [d for d in detections if d.label != PERSON_LABEL]

        ## Remember the nearest of each kind (lowest bottom edge), described the way an
        ## alert would describe it, for find()
        for detection in sorted(objects, key=lambda d: d.box[3]):
            self.last_seen[detection.label] = (now, describe_object(detection.box, user, frame_width, frame_height),
                                               pan_of_box(detection.box, frame_width))

        in_path = [d for d in objects if is_in_path(d.box, user, frame_width, frame_height)]
        announcements = []

        ## Nearest first: the lower an object's bottom edge, the closer it is to the user
        for detection in sorted(in_path, key=lambda d: d.box[3], reverse=True):
            ## Track IDs on objects flip around a lot, so the cooldown is per label
            if now - self.last_announced.get(detection.label, float("-inf")) < self.cooldown_s:
                continue

            self.last_announced[detection.label] = now
            position = position_in_path(detection.box, user, frame_width)
            pan = pan_of_box(detection.box, frame_width)
            announcements.append((detection.label, position, f"{detection.label} {position}", pan))

        return announcements

    def find(self, label):
        """Answer to WHERE_IS, for any object seen anywhere in view (not only the path),
        e.g. "Cup on your left", "Cup ahead, seen 5 seconds ago", "I don't see a cup"."""
        label = label.lower()
        seen = self.last_seen.get(label)
        if seen is None or self.clock() - seen[0] > REMEMBER_S:
            return f"I don't see {article(label)} {label}"

        seen_at, position, _ = seen
        answer = f"{label.capitalize()} {position}"
        ago = self.clock() - seen_at
        if ago > RECENT_S:
            answer += f", seen {round(ago)} seconds ago"
        return answer


    def pan_of(self, label):
        """Which side the last-seen object of this kind was on, for stereo (0.0 if unknown)."""
        seen = self.last_seen.get(label.lower())
        return seen[2] if seen else 0.0


def describe_object(box, user, frame_width, frame_height):
    """Position words for any object: relative to the user's path when it's in it,
    otherwise just which side of the view it's on."""
    if is_in_path(box, user, frame_width, frame_height):
        return position_in_path(box, user, frame_width)
    return describe_position(get_horizontal_error(box, frame_width))


def pan_of_box(box, frame_width):
    return max(-1.0, min(1.0, get_horizontal_error(box, frame_width)))


def path_bounds(user, frame_width):
    """Left and right edges of the user's path, in pixels."""
    if user is None:
        return NO_USER_PATH[0] * frame_width, NO_USER_PATH[1] * frame_width

    x1, y1, x2, y2 = user.box
    body_width = x2 - x1
    return x1 - PATH_SIDE_WIDTHS * body_width, x2 + PATH_SIDE_WIDTHS * body_width


def is_in_path(box, user, frame_width, frame_height):
    """Overlaps the path, is ahead of the user (its bottom edge above the user's feet),
    and not too far ahead (its bottom edge below PATH_FAR_EDGE)."""
    x1, y1, x2, y2 = box
    left, right = path_bounds(user, frame_width)
    overlaps = x2 > left and x1 < right
    ahead = user is None or y2 < user.box[3]
    near_enough = y2 >= PATH_FAR_EDGE * frame_height
    return overlaps and ahead and near_enough


def position_in_path(box, user, frame_width):
    """'ahead' when straight in front of the user, else which side of the path it's on."""
    if user is None:
        return describe_position(get_horizontal_error(box, frame_width))

    center_x = (box[0] + box[2]) / 2
    if center_x < user.box[0]:
        return "ahead on your left"
    if center_x > user.box[2]:
        return "ahead on your right"
    return "ahead"


def article(label):
    return "an" if label[:1] in "aeiou" else "a"
