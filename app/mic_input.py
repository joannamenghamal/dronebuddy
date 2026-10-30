import logging
import queue
from typing import List

from app.bridge_messages import VOICE_COMMAND_TYPE, parse_voice_command
from app.voice_commands import VoiceCommand

logger = logging.getLogger("dronebuddy.voice.mic")

MIN_CONFIDENCE = 0.5  # The phone should already drop worse recognitions; this is a second guard


class MicInput:
    """The user's voice commands, recognized on the phone (push-to-talk) and sent over
    the bridge as "voice_command" messages. Same interface as FakeMic.

    The bridge delivers messages on its own thread; they wait in a queue until the
    main loop's next poll()."""

    def __init__(self, drone, min_confidence=MIN_CONFIDENCE):
        self.min_confidence = min_confidence
        self.listening = False
        self.pending = queue.Queue()
        ## Registered right away so commands sent just after connecting aren't lost
        drone.add_message_handler(VOICE_COMMAND_TYPE, self._on_message)

    def start(self) -> None:
        self.listening = True

    def stop(self) -> None:
        self.listening = False

    def poll(self) -> List[VoiceCommand]:
        """Commands received since the last call. Non-blocking."""
        commands = []
        while True:
            try:
                commands.append(self.pending.get_nowait())
            except queue.Empty:
                return commands

    def _on_message(self, message: dict) -> None:
        if not self.listening:
            return

        command = parse_voice_command(message)
        if command is None:
            logger.warning("ignoring malformed voice_command from the phone: %r", message)
            return
        if command.confidence < self.min_confidence:
            logger.info("ignoring low-confidence voice command %s (%.2f)", command.type.name, command.confidence)
            return

        self.pending.put(command)
