from enum import Enum

import pytest

from app.bridge_messages import parse_voice_command, say_message
from app.voice_commands import CommandType, FakeMic, VoiceCommand, parse_script


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now


def test_fake_mic_hands_out_each_command_once_when_due():
    clock = FakeClock()
    mic = FakeMic([(4, VoiceCommand(CommandType.WHERE_IS, "car")), (1, VoiceCommand(CommandType.REPEAT))], clock)

    assert mic.poll() == []  # not started yet
    mic.start()

    clock.now = 0.5
    assert mic.poll() == []
    clock.now = 1.0
    assert [c.type for c in mic.poll()] == [CommandType.REPEAT]
    clock.now = 10
    assert mic.poll() == [VoiceCommand(CommandType.WHERE_IS, "car")]
    assert mic.poll() == []


def test_parse_script():
    script = parse_script("4:where_is:Car, 9:REPEAT ,15:STOP_SESSION")

    assert [(at, c.type, c.argument) for at, c in script] == [
        (4.0, CommandType.WHERE_IS, "car"),
        (9.0, CommandType.REPEAT, None),
        (15.0, CommandType.STOP_SESSION, None),
    ]


def test_parse_script_rejects_unknown_commands():
    with pytest.raises(ValueError):
        parse_script("3:DANCE")
    with pytest.raises(ValueError):
        parse_script("3")


def test_say_message_matches_the_bridge_format():
    class Priority(Enum):  # stand-in for audio_output.Priority; only its name is sent
        URGENT = 1

    assert say_message("Chair ahead", Priority.URGENT, pan=-1.7, volume=0.8) == {
        "type": "say", "text": "Chair ahead", "priority": "URGENT", "pan": -1.0, "volume": 0.8,
    }


def test_parse_voice_command_from_the_phone():
    command = parse_voice_command({"type": "voice_command", "command": "WHERE_IS", "argument": "Cup",
                                   "heard": "where is my mug", "confidence": 0.82})

    assert command == VoiceCommand(CommandType.WHERE_IS, "cup", "where is my mug", 0.82)


def test_parse_voice_command_ignores_other_and_malformed_messages():
    assert parse_voice_command({"type": "telemetry", "battery": 80}) is None
    assert parse_voice_command({"type": "voice_command", "command": "DANCE"}) is None
    assert parse_voice_command({"type": "voice_command"}) is None
    assert parse_voice_command({"type": "voice_command", "command": "REPEAT", "confidence": "high"}) is None
