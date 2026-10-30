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


## The user, kept at the bottom-middle of the frame: 160 px wide, so the path runs
## one body-width either side of them: x = 400 .. 880
USER = Detection("person", (560, 360, 720, FRAME_H), 1)


class ObjectLocatorTests(unittest.TestCase):
    def test_only_objects_in_the_users_path_are_announced_nearest_first(self):
        locator = ObjectLocator(cooldown_s=10, clock=FakeClock())

        chair_ahead = Detection("chair", (600, 200, 700, 330))
        bench_ahead_left = Detection("bench", (420, 250, 520, 340))   # nearer: lower in the frame
        car_off_to_the_side = Detection("car", (0, 100, 300, 250))   # outside the path
        bag_beside_the_user = Detection("backpack", (600, 650, 650, FRAME_H))  # not ahead of them
        someone = Detection("person", (640, 100, 700, 300), 2)       # people go to the TrackingModule

        detections = [chair_ahead, bench_ahead_left, car_off_to_the_side, bag_beside_the_user, someone]
        result = locator.locate(detections, USER, FRAME_W, FRAME_H)

        self.assertEqual([(label, message) for label, _, message, _ in result], [
            ("bench", "bench ahead on your left"),
            ("chair", "chair ahead"),
        ])
        self.assertLess(result[0][3], 0)  # the bench's sound comes from the left

        ## Each kind of object only once per cooldown
        self.assertEqual(locator.locate(detections, USER, FRAME_W, FRAME_H), [])

    def test_objects_far_ahead_are_not_announced_but_find_still_knows_them(self):
        locator = ObjectLocator(clock=FakeClock())

        ## In the corridor, but its bottom edge is above the path's far edge (0.40 of the frame)
        far_car = Detection("car", (600, 50, 700, 200))

        self.assertEqual(locator.locate([far_car], USER, FRAME_W, FRAME_H), [])
        self.assertEqual(locator.find("car"), "Car ahead")

    def test_without_the_user_in_view_the_middle_third_is_the_path(self):
        locator = ObjectLocator(clock=FakeClock())

        result = locator.locate([Detection("chair", (500, 300, 700, 500)), Detection("car", (0, 100, 300, 250))],
                                None, FRAME_W, FRAME_H)

        self.assertEqual([message for _, _, message, _ in result], ["chair ahead"])

    def test_find_answers_for_any_object_seen_anywhere_in_view(self):
        clock = FakeClock()
        locator = ObjectLocator(clock=clock)

        locator.locate([Detection("car", (0, 100, 300, 250))], USER, FRAME_W, FRAME_H)  # not in the path

        self.assertEqual(locator.find("Car"), "Car on your left")
        self.assertLess(locator.pan_of("car"), 0)
        self.assertEqual(locator.find("cup"), "I don't see a cup")
        self.assertEqual(locator.find("umbrella"), "I don't see an umbrella")

        clock.now = 5
        self.assertEqual(locator.find("car"), "Car on your left, seen 5 seconds ago")

        clock.now = 31
        self.assertEqual(locator.find("car"), "I don't see a car")

    def test_find_remembers_the_nearest_one_described_like_the_alerts(self):
        locator = ObjectLocator(clock=FakeClock())

        far_car_left = Detection("car", (0, 100, 300, 250))
        near_car_ahead = Detection("car", (600, 300, 700, 340))
        locator.locate([near_car_ahead, far_car_left], USER, FRAME_W, FRAME_H)

        self.assertEqual(locator.find("car"), "Car ahead")


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
