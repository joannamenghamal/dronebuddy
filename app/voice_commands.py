"""Voice commands: the contract between the mic side (the phone, which recognizes
speech while the push-to-talk screen is held) and the speaker side (the assistant,
which answers every command out loud).

Command names here must match the Android app's exactly."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class CommandType(Enum):
    START_SESSION = "START_SESSION"
    STOP_SESSION = "STOP_SESSION"
    WHERE_IS = "WHERE_IS"
    REPEAT = "REPEAT"
    LOUDER = "LOUDER"
    QUIETER = "QUIETER"


@dataclass
class VoiceCommand:
    type: CommandType
    argument: Optional[str] = None  # WHERE_IS: a YOLO class name, e.g. "cup"
    heard_text: str = ""            # what speech-to-text heard, for the session log
    confidence: float = 1.0


class FakeMic:
    """Stands in for the phone's microphone: hands out scripted commands at set times,
    so the speaker side can be built and tested without a phone.

    Same interface as the real MicInput: start(), stop(), poll().
    script: list of (seconds after start(), VoiceCommand)."""

    def __init__(self, script, clock=time.monotonic):
        self.script = sorted(script, key=lambda item: item[0])
        self.clock = clock
        self.started_at = None

    def start(self) -> None:
        self.started_at = self.clock()

    def stop(self) -> None:
        self.started_at = None

    def poll(self) -> List[VoiceCommand]:
        """Commands that came due since the last call. Non-blocking."""
        if self.started_at is None:
            return []

        elapsed = self.clock() - self.started_at
        due = [command for at, command in self.script if at <= elapsed]
        self.script = [(at, command) for at, command in self.script if at > elapsed]
        return due


def parse_script(text):
    """Parses a --voice-script value: comma-separated "seconds:COMMAND[:argument]",
    e.g. "4:WHERE_IS:car, 9:REPEAT, 15:STOP_SESSION"."""
    script = []
    for entry in (part.strip() for part in text.split(",")):
        if not entry:
            continue

        fields = [field.strip() for field in entry.split(":")]
        if len(fields) not in (2, 3):
            raise ValueError(f"bad voice script entry {entry!r}: expected seconds:COMMAND[:argument]")

        command_type = CommandType(fields[1].upper())
        argument = fields[2].lower() if len(fields) == 3 else None
        script.append((float(fields[0]), VoiceCommand(command_type, argument, heard_text=entry)))

    return script
