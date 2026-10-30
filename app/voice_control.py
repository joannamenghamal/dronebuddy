import logging

from app.audio_output import VOLUME_STEP, Priority
from app.voice_commands import CommandType

logger = logging.getLogger("dronebuddy.voice")


class VoiceControl:
    """Answers the user's voice commands out loud. Every answer is URGENT: the user
    just asked, so it goes ahead of routine alerts.

    handle() returns False when the session should end (STOP_SESSION); the main loop
    then says "Session ended" as it shuts down."""

    def __init__(self, audio, locator, session_log=None):
        self.audio = audio
        self.locator = locator
        self.session_log = session_log

    def handle(self, command) -> bool:
        logger.info("voice command %s %s (heard %r)", command.type.name, command.argument or "", command.heard_text)
        self._log("voice_command", command=command.type.name, argument=command.argument,
                  heard=command.heard_text, confidence=round(command.confidence, 2))

        if command.type == CommandType.STOP_SESSION:
            return False

        if command.type == CommandType.START_SESSION:
            self._answer("Visual Buddy ready", repeatable=False)
        elif command.type == CommandType.WHERE_IS:
            if command.argument:
                ## The answer comes from the object's side, like the alerts
                self._answer(self.locator.find(command.argument), pan=self.locator.pan_of(command.argument))
            else:
                self._answer("Which object?", repeatable=False)
        elif command.type == CommandType.REPEAT:
            if not self.audio.repeat_last():
                self._answer("Nothing to repeat yet", repeatable=False)
        elif command.type == CommandType.LOUDER:
            self.audio.change_volume(+VOLUME_STEP)
            self._answer("Louder", repeatable=False)
        elif command.type == CommandType.QUIETER:
            self.audio.change_volume(-VOLUME_STEP)
            self._answer("Quieter", repeatable=False)

        return True

    def _answer(self, text, pan=0.0, repeatable=True):
        self._log("voice_answer", message=text)
        self.audio.say(text, Priority.URGENT, pan, repeatable)

    def _log(self, event, **details):
        if self.session_log is not None:
            self.session_log.log(event, **details)
