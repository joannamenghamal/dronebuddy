"""Unit tests for the Visual Buddy decision logic: tracking, alerts, object
announcements and user selection. No camera, model or drone needed."""
import unittest

from app.audio_output import Priority
from app.compute_actions import ComputeActions
from app.detection_module import Detection
from app.object_locator import ObjectLocator
from app.person_tracker import describe_position, get_head_ratio, is_head_cut_off, select_user
from app.tracking_module import APPROACHING, LEFT_FRAME, NEW, STANDING_STILL, TrackingModule

FRAME_W, FRAME_H = 1280, 720
FPS = 10


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def person(track_id, center_x, height):
    """A person Detection centered at center_x, standing on the bottom of the frame."""
    width = height * 0.4
    return Detection("person", (center_x - width / 2, FRAME_H - height, center_x + width / 2, FRAME_H), track_id)


def texts(alerts):
    return [alert.text for alert in alerts]


def confirm(tracking, clock, people):
    """Keeps the same people in view long enough to be confirmed, returns all events."""
    return run_frames(tracking, clock, [people] * (FPS + 1))


def run_frames(tracking, clock, frames):
    """Feeds a list of per-frame people lists through the tracker, returns all events."""
    events = []
    for people in frames:
        events += tracking.update(people, FRAME_W, FRAME_H)
        clock.now += 1 / FPS
    return events


class TrackingModuleTests(unittest.TestCase):
    def test_new_person_then_standing_still(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)

        events = run_frames(tracking, clock, [[person(1, 640, 300)]] * 20)

        activities = [e.activity for e in events]
        self.assertEqual(activities[0], NEW)
        self.assertIn(STANDING_STILL, activities)

    def test_growing_box_is_approaching(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)

        ## Box grows from 200px to 500px over 2 seconds
        frames = [[person(1, 640, 200 + i * 15)] for i in range(20)]
        events = run_frames(tracking, clock, frames)

        self.assertIn(APPROACHING, [e.activity for e in events])

    def test_brief_false_detection_is_never_reported(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)

        ## A "person" (e.g. a tree trunk) seen for 3 frames, then gone
        frames = [[person(9, 100, 80)]] * 3 + [[]] * 20
        self.assertEqual(run_frames(tracking, clock, frames), [])

    def test_person_disappearing_left_frame(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)

        frames = [[person(1, 640, 300)]] * 10 + [[]] * 15
        events = run_frames(tracking, clock, frames)

        self.assertEqual(events[-1].activity, LEFT_FRAME)
        self.assertIsNone(tracking.activity_of(1))


class ComputeActionsTests(unittest.TestCase):
    def test_alert_text_and_cooldown(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)
        actions = ComputeActions(cooldown_s=5, clock=clock)

        events = confirm(tracking, clock, [person(1, 100, 300)])
        self.assertEqual(texts(actions.compute(events)), ["Person on your left"])

        ## Same event again within the cooldown is not repeated
        self.assertEqual(actions.compute(events), [])

        clock.now += 6
        self.assertEqual(texts(actions.compute(events)), ["Person on your left"])

    def test_two_people_same_message_spoken_once(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)
        actions = ComputeActions(clock=clock)

        events = confirm(tracking, clock, [person(1, 640, 300), person(2, 660, 300)])
        self.assertEqual(texts(actions.compute(events)), ["Person ahead"])

    def test_approaching_is_urgent_and_comes_from_the_persons_side(self):
        clock = FakeClock()
        tracking = TrackingModule(clock)
        actions = ComputeActions(clock=clock)

        ## Confirmed on the right, then their box grows: approaching
        confirm(tracking, clock, [person(1, 1100, 200)])
        events = run_frames(tracking, clock, [[person(1, 1100, 200 + i * 15)] for i in range(20)])
        approaching = [a for a in actions.compute(events) if a.text.startswith("Person approaching")]

        self.assertEqual(len(approaching), 1)
        self.assertEqual(approaching[0].priority, Priority.URGENT)
        self.assertGreater(approaching[0].pan, 0.5)


class ObjectLocatorTests(unittest.TestCase):
    def test_only_close_objects_announced_once(self):
        clock = FakeClock()
        locator = ObjectLocator(cooldown_s=10, clock=clock)

        near_chair = Detection("chair", (1000, 300, 1250, 700))  # 400px tall = 0.56 of frame
        far_cup = Detection("cup", (600, 300, 620, 330))
        someone = Detection("person", (0, 0, 640, 720), 1)

        result = locator.locate([near_chair, far_cup, someone], FRAME_W, FRAME_H)
        self.assertEqual(result, [("chair", "on your right", "chair on your right")])

        self.assertEqual(locator.locate([near_chair], FRAME_W, FRAME_H), [])


class UserSelectionTests(unittest.TestCase):
    def test_user_is_person_at_bottom_middle(self):
        user = Detection("person", (860, 400, 1060, FRAME_H), 3)       # Bottom-middle, feet cut off
        passerby = Detection("person", (100, 100, 250, 500), 4)        # Up and to the left
        bigger_passerby = Detection("person", (1000, 0, 1280, 700), 5)  # Bigger, but off to the side

        self.assertEqual(select_user([passerby, bigger_passerby, user], None, FRAME_W, FRAME_H).track_id, 3)
        self.assertIsNone(select_user([], None, FRAME_W, FRAME_H))

    def test_stays_locked_on_same_user(self):
        user = Detection("person", (100, 100, 250, 500), 3)
        newcomer = Detection("person", (860, 400, 1060, FRAME_H), 9)  # Now closer to bottom-middle

        self.assertEqual(select_user([newcomer, user], 3, FRAME_W, FRAME_H).track_id, 3)

    def test_describe_position(self):
        self.assertEqual(describe_position(-0.8), "on your left")
        self.assertEqual(describe_position(0.0), "ahead")
        self.assertEqual(describe_position(0.8), "on your right")


class HeadPositionTests(unittest.TestCase):
    def test_feet_cut_off_is_normal_but_head_cut_off_is_detected(self):
        ## User at bottom-middle with feet cut off: still a valid distance from the head
        user = (860, 430, 1060, FRAME_H)
        self.assertFalse(is_head_cut_off(user, FRAME_H))
        self.assertAlmostEqual(get_head_ratio(user, FRAME_H), 430 / FRAME_H)

        ## Head out of the top of the frame: no distance estimate
        tall = (860, 0, 1060, 600)
        self.assertTrue(is_head_cut_off(tall, FRAME_H))


if __name__ == "__main__":
    unittest.main()
