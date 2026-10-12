## Visual Buddy setup: the drone flies behind and slightly above the visually impaired user,
## keeping them at the bottom-middle of the frame so the camera sees what's ahead of them.
##
## All thresholds are fractions of the frame, so they work at any resolution
## (webcam 640x480, DJI Mini 3 stream 1280x720 / 1920x1080, recorded clips...)
DEAD_ZONE = 0.10          # +/- fraction of half-frame width counted as "CENTER"

## The user's feet are usually cut off by the bottom edge, so their box height is not a
## usable distance. The top of their head is: walking away moves it up toward the horizon,
## the drone getting too close moves it down.
TARGET_HEAD_RATIO = 0.40  # Head (box top) / frame height to hold the user at
                          # (measured in our DJI footage when the user was framed naturally)
HEAD_TOLERANCE = 0.08     # +/- around the target counted as "GOOD DISTANCE"
EDGE_MARGIN = 0.01        # Box top within this fraction of the top edge = head is cut off


def select_user(people, locked_id=None, frame_width=None, frame_height=None):
    """Picks the user (Detection) the drone is following. Stays locked on the same track ID
    while it's still in frame, otherwise picks the person closest to the bottom-middle of
    the frame, which is where the user is kept. Returns None if there are no people."""
    if not people:
        return None

    for person in people:
        if locked_id is not None and person.track_id == locked_id:
            return person

    return min(people, key=lambda person: distance_to_bottom_middle(person.box, frame_width, frame_height))


def distance_to_bottom_middle(box, frame_width, frame_height):
    """How far the person's feet are from the bottom-middle of the frame, as a fraction of the frame."""
    x1, y1, x2, y2 = box
    dx = ((x1 + x2) / 2 - frame_width / 2) / frame_width
    dy = (frame_height - y2) / frame_height
    return (dx ** 2 + dy ** 2) ** 0.5


def get_horizontal_error(box, frame_width):
    """How far the person is from the frame center: -1.0 = far left edge,
    0.0 = centered, +1.0 = far right edge."""
    x1, y1, x2, y2 = box

    ## Calculate center of the person's bounding box
    center_x = (x1 + x2) / 2

    frame_center_x = frame_width / 2

    return (center_x - frame_center_x) / frame_center_x


def get_height_ratio(box, frame_height):
    """Box height as a fraction of the frame height. Bigger ratio = person is closer.
    Used for other people walking around; the user is measured by their head instead."""
    x1, y1, x2, y2 = box

    return (y2 - y1) / frame_height


def get_head_ratio(box, frame_height):
    """Where the top of the person's head is: 0.0 = top of frame, 1.0 = bottom.
    Smaller = user is farther ahead of the drone."""
    x1, y1, x2, y2 = box

    return y1 / frame_height


def is_head_cut_off(box, frame_height, margin=EDGE_MARGIN):
    """True if the box touches the top of the frame, so we can't see where the head is
    and have no distance estimate for the user."""
    x1, y1, x2, y2 = box

    return y1 <= frame_height * margin


def get_direction(horizontal_error, dead_zone=DEAD_ZONE):
    ## Determine horizontal position
    if horizontal_error < -dead_zone:
        return "LEFT"
    elif horizontal_error > dead_zone:
        return "RIGHT"
    else:
        return "CENTER"


def describe_position(horizontal_error):
    """Spoken position for the user, splitting the frame into thirds. The camera faces the
    same way as the user, so the left of the frame is the user's left."""
    if horizontal_error < -1 / 3:
        return "on your left"
    elif horizontal_error > 1 / 3:
        return "on your right"
    else:
        return "ahead"


def get_distance_status(head_ratio, target=TARGET_HEAD_RATIO, tolerance=HEAD_TOLERANCE):
    ## Head high in the frame = user far ahead, head low = drone too close
    if head_ratio < target - tolerance:
        return "TOO FAR"
    elif head_ratio > target + tolerance:
        return "TOO CLOSE"
    else:
        return "GOOD DISTANCE"
