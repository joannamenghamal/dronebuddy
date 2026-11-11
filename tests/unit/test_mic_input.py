"""MicInput: voice commands from the phone arrive over the bridge on its own thread
and wait for the main loop's poll()."""

from app.main import build_mic, build_speech
from app.audio_output import BridgeSpeech, LocalSpeech, SilentSpeech
from app.mic_input import MicInput
from app.voice_commands import CommandType, FakeMic, VoiceCommand


class FakeDrone:
    """Just the bridge message hooks MicInput and BridgeSpeech use."""

    def __init__(self):
        self.handlers = {}
        self.sent = []

    def add_message_handler(self, msg_type, handler):
        self.handlers.setdefault(msg_type, []).append(handler)

    def send_message(self, payload):
        self.sent.append(payload)

    def deliver(self, message):
        for handler in self.handlers.get(message["type"], []):
            handler(message)


def test_commands_from_the_phone_wait_for_poll():
    drone = FakeDrone()
    mic = MicInput(drone)
    mic.start()

    drone.deliver({"type": "voice_command", "command": "WHERE_IS", "argument": "cup", "heard": "where is my mug", "confidence": 0.9})
    drone.deliver({"type": "voice_command", "command": "REPEAT", "confidence": 0.8})

    assert mic.poll() == [
        VoiceCommand(CommandType.WHERE_IS, "cup", "where is my mug", 0.9),
        VoiceCommand(CommandType.REPEAT, None, "", 0.8),
    ]
    assert mic.poll() == []


def test_low_confidence_malformed_and_not_listening_are_ignored():
    drone = FakeDrone()
    mic = MicInput(drone)

    drone.deliver({"type": "voice_command", "command": "REPEAT"})  # before start()
    mic.start()
    drone.deliver({"type": "voice_command", "command": "REPEAT", "confidence": 0.2})
    drone.deliver({"type": "voice_command", "command": "DANCE"})
    mic.stop()
    drone.deliver({"type": "voice_command", "command": "REPEAT"})  # after stop()

    assert mic.poll() == []


def test_dji_speaks_on_the_phone_and_listens_to_the_phone():
    drone = FakeDrone()

    assert isinstance(build_speech("dji", drone, muted=False), BridgeSpeech)
    assert isinstance(build_mic("dji", drone, None), MicInput)

    build_speech("dji", drone, muted=False).send({"type": "say", "text": "x"})
    assert drone.sent == [{"type": "say", "text": "x"}]


def test_mock_speaks_on_the_laptop_mute_is_silent_and_a_script_wins():
    drone = FakeDrone()

    assert isinstance(build_speech("mock", drone, muted=False), LocalSpeech)
    assert isinstance(build_speech("dji", drone, muted=True), SilentSpeech)
    assert build_mic("mock", drone, None) is None
    assert isinstance(build_mic("dji", drone, "3:REPEAT"), FakeMic)
