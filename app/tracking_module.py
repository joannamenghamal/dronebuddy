import time
from collections import deque
from dataclasses import dataclass

from person_tracker import get_height_ratio, get_horizontal_error

## Activities a tracked person can be in
NEW = "NEW"                        # First time this person (track ID) is seen
APPROACHING = "APPROACHING"
MOVING_AWAY = "MOVING AWAY"
STANDING_STILL = "STANDING STILL"
MOVING = "MOVING"                  # Moving sideways, distance roughly unchanged
LEFT_FRAME = "LEFT FRAME"

HISTORY_SECONDS = 1.0     # How much recent movement we look at to decide the activity
MIN_HISTORY_SECONDS = 0.5  # Need at least this much history before classifying
APPROACH_RATE = 0.10      # Box-height-ratio change per second that counts as approaching / moving away
STILL_RATE = 0.10         # Max horizontal-error change per second that still counts as standing still
CONFIRM_FRAMES = 3        # A new activity must hold this many frames in a row (filters box jitter)
CONFIRM_TRACK_S = 0.5     # A person must stay in view this long before we report them at all
                          # (brief false detections, e.g. tree trunks, never get announced)
LEFT_FRAME_AFTER_S = 1.0  # Unseen this long -> person has left the frame


@dataclass
class ActivityEvent:
    track_id: int
    activity: str
    horizontal_error: float  # -1 left edge .. +1 right edge, where the person was
    height_ratio: float      # Box height / frame height, bigger = closer


class PersonTrack:
    """Recent position history of one person, identified by their ByteTrack ID."""

    def __init__(self, track_id, first_seen):
        self.track_id = track_id
        self.first_seen = first_seen
        self.confirmed = False  # True once seen for CONFIRM_TRACK_S - only then is it reported
        self.history = deque()  # (time, horizontal_error, height_ratio)
        self.activity = None
        self.candidate = None
        self.candidate_frames = 0

    def add_sample(self, now, horizontal_error, height_ratio):
        self.history.append((now, horizontal_error, height_ratio))

        ## Drop samples that are too old to matter
        while now - self.history[0][0] > HISTORY_SECONDS:
            self.history.popleft()

    def last_seen(self):
        return self.history[-1][0]

    def latest(self):
        _, horizontal_error, height_ratio = self.history[-1]
        return horizontal_error, height_ratio

    def classify(self):
        """Works out the current activity from how the box changed over the history window."""
        start_time, start_error, start_ratio = self.history[0]
        end_time, end_error, end_ratio = self.history[-1]

        elapsed = end_time - start_time
        if elapsed < MIN_HISTORY_SECONDS:
            return None  # Not enough history yet

        ## Box getting taller = person getting closer
        size_rate = (end_ratio - start_ratio) / elapsed
        side_rate = abs(end_error - start_error) / elapsed

        if size_rate > APPROACH_RATE:
            return APPROACHING
        elif size_rate < -APPROACH_RATE:
            return MOVING_AWAY
        elif side_rate < STILL_RATE:
            return STANDING_STILL
        else:
            return MOVING

    def update_activity(self):
        """Returns the new activity if it changed (and held for CONFIRM_FRAMES), otherwise None."""
        activity = self.classify()

        if activity is None or activity == self.activity:
            self.candidate = None
            self.candidate_frames = 0
            return None

        if activity == self.candidate:
            self.candidate_frames += 1
        else:
            self.candidate = activity
            self.candidate_frames = 1

        if self.candidate_frames >= CONFIRM_FRAMES:
            self.activity = activity
            self.candidate = None
            self.candidate_frames = 0
            return activity

        return None


class TrackingModule:
    """Follows every tracked person over time and reports when their activity changes."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.tracks = {}  # track_id -> PersonTrack

    def update(self, people, frame_width, frame_height):
        """people: person Detections for this frame. Returns a list of ActivityEvents."""
        now = self.clock()
        events = []

        for person in people:
            if person.track_id is None:
                continue  # Tracker hasn't confirmed this person yet

            horizontal_error = get_horizontal_error(person.box, frame_width)
            height_ratio = get_height_ratio(person.box, frame_height)

            track = self.tracks.get(person.track_id)
            if track is None:
                track = PersonTrack(person.track_id, now)
                self.tracks[person.track_id] = track

            track.add_sample(now, horizontal_error, height_ratio)

            ## Only report people who have been in view long enough to be real
            if not track.confirmed:
                if now - track.first_seen < CONFIRM_TRACK_S:
                    continue
                track.confirmed = True
                events.append(ActivityEvent(person.track_id, NEW, horizontal_error, height_ratio))

            activity = track.update_activity()
            if activity is not None:
                events.append(ActivityEvent(person.track_id, activity, horizontal_error, height_ratio))

        ## Anyone we haven't seen for a while has left the frame
        for track_id, track in list(self.tracks.items()):
            if now - track.last_seen() > LEFT_FRAME_AFTER_S:
                ## Never announced -> leave silently too
                if track.confirmed:
                    horizontal_error, height_ratio = track.latest()
                    events.append(ActivityEvent(track_id, LEFT_FRAME, horizontal_error, height_ratio))
                del self.tracks[track_id]

        return events

    def activity_of(self, track_id):
        track = self.tracks.get(track_id)
        return track.activity if track and track.confirmed else None
