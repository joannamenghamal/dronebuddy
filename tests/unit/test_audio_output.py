"""AudioOutput: queue order, dropping stale alerts, REPEAT, volume, and the phone backend.
Uses recording backends instead of real speech."""

import threading
import time

from app.audio_output import MIN_VOLUME, AudioOutput, BridgeSpeech, Priority, SilentSpeech


class HeldSpeech(SilentSpeech):
    """Holds the first utterance 'in the user's ear' until released, so the test can
    queue more behind it and check the order they come out in."""

    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def speak(self, utterance):
        super().speak(utterance)
        if len(self.spoken) == 1:
            self.started.set()
            self.release.wait(timeout=5)


def spoken_texts(backend):
    return [u.text for u in backend.spoken]


def wait_until(condition, timeout_s=5.0):
    """Polls a condition set by AudioOutput's own thread."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_urgent_alerts_go_ahead_of_waiting_normal_ones():
    backend = HeldSpeech()
    audio = AudioOutput(backend=backend)

    audio.say("Visual Buddy ready")
    assert backend.started.wait(timeout=5)
    audio.say("car on your right")
    audio.say("Person approaching, ahead", Priority.URGENT)
    audio.say("Cup on your left", Priority.URGENT)
    backend.release.set()
    audio.close()

    assert spoken_texts(backend) == ["Visual Buddy ready", "Person approaching, ahead", "Cup on your left", "car on your right"]


def test_oldest_normal_alert_is_dropped_when_speech_falls_behind():
    backend = HeldSpeech()
    audio = AudioOutput(backend=backend)

    audio.say("first")
    assert backend.started.wait(timeout=5)
    audio.say("old normal")
    audio.say("urgent", Priority.URGENT)
    audio.say("newer normal")
    audio.say("newest normal")  # 4 waiting > MAX_PENDING: "old normal" goes
    backend.release.set()
    audio.close()

    assert spoken_texts(backend) == ["first", "urgent", "newer normal", "newest normal"]


def test_repeat_last_says_the_last_thing_again_urgently():
    backend = SilentSpeech()
    audio = AudioOutput(backend=backend)

    assert audio.repeat_last() is False  # nothing said yet
    audio.say("Person ahead")
    assert wait_until(lambda: audio.last_spoken == "Person ahead")

    assert audio.repeat_last() is True
    audio.close()

    assert spoken_texts(backend) == ["Person ahead", "Person ahead"]
    assert backend.spoken[-1].priority == Priority.URGENT


def test_volume_steps_stay_in_range_and_apply_to_what_is_said_next():
    backend = SilentSpeech()
    audio = AudioOutput(backend=backend)

    assert audio.change_volume(+0.2) == 1.0  # already at the top
    for _ in range(10):
        audio.change_volume(-0.2)
    assert audio.volume == MIN_VOLUME

    audio.say("Quieter")
    audio.close()
    assert backend.spoken[0].volume == MIN_VOLUME


def test_pan_is_kept_between_left_and_right_ear():
    backend = SilentSpeech()
    audio = AudioOutput(backend=backend)
    audio.say("chair on your left", pan=-3.0)
    audio.close()

    assert backend.spoken[0].pan == -1.0


def test_bridge_speech_sends_say_messages_to_the_phone():
    sent = []
    audio = AudioOutput(backend=BridgeSpeech(sent.append))
    audio.say("Person approaching, ahead", Priority.URGENT, pan=0.25)
    audio.close()

    assert sent == [{"type": "say", "text": "Person approaching, ahead", "priority": "URGENT", "pan": 0.25, "volume": 1.0}]


def test_a_failing_backend_does_not_stop_later_alerts():
    class Flaky(SilentSpeech):
        def speak(self, utterance):
            super().speak(utterance)
            if utterance.text == "boom":
                raise RuntimeError("audio device lost")

    backend = Flaky()
    audio = AudioOutput(backend=backend)
    audio.say("boom")
    audio.say("still talking")
    audio.close()

    assert spoken_texts(backend) == ["boom", "still talking"]


def test_repeat_comes_from_the_same_side_as_the_original():
    backend = SilentSpeech()
    audio = AudioOutput(backend=backend)

    audio.say("Car on your left", pan=-0.7)
    assert wait_until(lambda: audio.last_spoken == "Car on your left")
    audio.repeat_last()
    audio.close()

    assert [u.pan for u in backend.spoken] == [-0.7, -0.7]
