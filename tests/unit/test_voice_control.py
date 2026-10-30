"""VoiceControl: every command gets a spoken, urgent answer; STOP_SESSION ends the session."""

import time

from app.audio_output import AudioOutput, Priority, SilentSpeech
from app.object_locator import ObjectLocator
from app.voice_commands import CommandType, VoiceCommand
from app.voice_control import VoiceControl
from app.detection_module import Detection


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now


class RecordingLog:
    def __init__(self):
        self.events = []

    def log(self, event, **details):
        self.events.append((event, details))


def make():
    backend = SilentSpeech()
    audio = AudioOutput(backend=backend)
    locator = ObjectLocator(clock=FakeClock())
    log = RecordingLog()
    return VoiceControl(audio, locator, log), audio, backend, locator, log


def said(audio, backend):
    audio.close()
    return [(u.text, u.priority) for u in backend.spoken]


def test_where_is_answers_from_what_the_camera_has_seen():
    voice, audio, backend, locator, log = make()
    locator.locate([Detection("cup", (0, 300, 100, 400))], None, 1280, 720)

    assert voice.handle(VoiceCommand(CommandType.WHERE_IS, "cup", "where is my mug")) is True
    assert voice.handle(VoiceCommand(CommandType.WHERE_IS, "chair")) is True
    assert voice.handle(VoiceCommand(CommandType.WHERE_IS)) is True

    assert said(audio, backend) == [
        ("Cup on your left", Priority.URGENT),
        ("I don't see a chair", Priority.URGENT),
        ("Which object?", Priority.URGENT),
    ]
    assert log.events[0] == ("voice_command", {"command": "WHERE_IS", "argument": "cup", "heard": "where is my mug", "confidence": 1.0})
    assert ("voice_answer", {"message": "Cup on your left"}) in log.events


def test_louder_and_quieter_change_the_volume_and_confirm():
    voice, audio, backend, _, _ = make()

    voice.handle(VoiceCommand(CommandType.QUIETER))
    assert audio.volume == 0.8
    voice.handle(VoiceCommand(CommandType.LOUDER))
    assert audio.volume == 1.0

    assert [text for text, _ in said(audio, backend)] == ["Quieter", "Louder"]


def test_repeat_with_nothing_said_yet_says_so():
    voice, audio, backend, _, _ = make()

    voice.handle(VoiceCommand(CommandType.REPEAT))

    assert said(audio, backend) == [("Nothing to repeat yet", Priority.URGENT)]


def test_start_confirms_and_stop_ends_the_session():
    voice, audio, backend, _, log = make()

    assert voice.handle(VoiceCommand(CommandType.START_SESSION)) is True
    assert voice.handle(VoiceCommand(CommandType.STOP_SESSION)) is False

    assert said(audio, backend) == [("Visual Buddy ready", Priority.URGENT)]
    assert [event for event, _ in log.events].count("voice_command") == 2


def test_repeat_skips_confirmations_and_repeats_the_last_answer():
    voice, audio, backend, locator, _ = make()
    locator.locate([Detection("cup", (0, 300, 100, 400))], None, 1280, 720)

    voice.handle(VoiceCommand(CommandType.WHERE_IS, "cup"))
    voice.handle(VoiceCommand(CommandType.QUIETER))
    wait_spoken(backend, 2)
    voice.handle(VoiceCommand(CommandType.REPEAT))

    assert [text for text, _ in said(audio, backend)] == ["Cup on your left", "Quieter", "Cup on your left"]


def test_where_is_answer_comes_from_the_objects_side():
    voice, audio, backend, locator, _ = make()
    locator.locate([Detection("chair", (1100, 300, 1250, 400))], None, 1280, 720)

    voice.handle(VoiceCommand(CommandType.WHERE_IS, "chair"))
    audio.close()

    assert backend.spoken[0].text == "Chair on your right"
    assert backend.spoken[0].pan > 0.5


def wait_spoken(backend, count, timeout_s=5.0):
    """Waits for AudioOutput's own thread to have spoken `count` utterances."""
    deadline = time.monotonic() + timeout_s
    while len(backend.spoken) < count and time.monotonic() < deadline:
        time.sleep(0.01)
