import logging
import threading
from dataclasses import dataclass
from enum import IntEnum

from app.bridge_messages import say_message

logger = logging.getLogger("dronebuddy.audio")

MAX_PENDING = 3       # Old alerts are dropped if speech falls behind - stale cues are worse than none
VOLUME_STEP = 0.2     # LOUDER / QUIETER change the volume by this much
MIN_VOLUME = 0.2      # Never so quiet the user can't hear the next warning


class Priority(IntEnum):
    NORMAL = 0
    URGENT = 1  # Jumps the queue: people approaching, answers to the user's own questions


@dataclass
class Utterance:
    text: str
    priority: Priority = Priority.NORMAL
    pan: float = 0.0     # -1.0 = left ear .. +1.0 = right ear
    volume: float = 1.0  # 0.0 .. 1.0
    repeatable: bool = True  # False for confirmations ("Louder"), so REPEAT skips them


## ---- Speech backends: where the words actually come out ----

class LocalSpeech:
    """Laptop speakers via offline text-to-speech (pyttsx3), for --drone mock and demos.
    Mono, so pan is ignored, and a sentence already playing can't be cut off."""

    def __init__(self, rate=180):
        self.rate = rate
        self.engine = None
        self.unavailable = False

    def speak(self, utterance: Utterance) -> None:
        ## The engine must be created on the thread that uses it: AudioOutput's own thread
        if self.engine is None and not self.unavailable:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", self.rate)
            except Exception as error:
                logger.warning("text-to-speech unavailable (%s), logging alerts only", error)
                self.unavailable = True

        if self.engine is not None:
            self.engine.setProperty("volume", utterance.volume)
            self.engine.say(utterance.text)
            self.engine.runAndWait()


class SilentSpeech:
    """For --mute and tests: says nothing, remembers what would have been said."""

    def __init__(self):
        self.spoken = []

    def speak(self, utterance: Utterance) -> None:
        self.spoken.append(utterance)


class BridgeSpeech:
    """The user's phone speaks: each utterance is sent over the bridge as a "say"
    message, and the phone handles stereo, tones and cutting off a sentence for an
    urgent one. send is the bridge connection's send-a-message function."""

    def __init__(self, send):
        self.send = send

    def speak(self, utterance: Utterance) -> None:
        self.send(say_message(utterance.text, utterance.priority, utterance.pan, utterance.volume))


class AudioOutput:
    """Speaks alerts to the user on a background thread, so the video loop never waits.

    - URGENT alerts go ahead of NORMAL ones still waiting
    - At most MAX_PENDING alerts wait; the oldest NORMAL one is dropped first
    - Remembers the last thing said, for REPEAT, and a volume for LOUDER / QUIETER"""

    def __init__(self, backend=None, rate=180, muted=False):
        self.backend = backend or (SilentSpeech() if muted else LocalSpeech(rate))
        self.volume = 1.0
        self.last_spoken = None
        self.pending = []  # Utterances waiting, in the order they will be spoken
        self.closing = False
        self.condition = threading.Condition()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def say(self, text, priority=Priority.NORMAL, pan=0.0, repeatable=True):
        utterance = Utterance(text, Priority(priority), max(-1.0, min(1.0, pan)), self.volume, repeatable)

        with self.condition:
            if utterance.priority == Priority.URGENT:
                ## Behind other urgent alerts, ahead of every normal one
                position = sum(1 for u in self.pending if u.priority == Priority.URGENT)
                self.pending.insert(position, utterance)
            else:
                self.pending.append(utterance)

            ## Keep the queue short so the user always hears what's happening *now*
            while len(self.pending) > MAX_PENDING:
                drop = next((i for i, u in enumerate(self.pending) if u.priority == Priority.NORMAL), 0)
                logger.info("dropped stale alert %r", self.pending.pop(drop).text)

            self.condition.notify()

    def repeat_last(self) -> bool:
        """Says the last alert or answer again (REPEAT), skipping confirmations like
        "Louder". False if there is nothing to repeat yet."""
        if self.last_spoken is None:
            return False
        self.say(self.last_spoken, Priority.URGENT)
        return True

    def change_volume(self, step) -> float:
        """LOUDER / QUIETER. Returns the new volume, kept between MIN_VOLUME and 1.0."""
        self.volume = round(max(MIN_VOLUME, min(1.0, self.volume + step)), 2)
        return self.volume

    def close(self, timeout_s=5.0):
        """Finishes speaking what's queued (e.g. "Session ended"), then stops."""
        with self.condition:
            self.closing = True
            self.condition.notify()
        self.thread.join(timeout_s)

    def _run(self):
        while True:
            with self.condition:
                while not self.pending and not self.closing:
                    self.condition.wait()
                if not self.pending:
                    break
                utterance = self.pending.pop(0)

            logger.info("say %r (%s, pan %+.1f)", utterance.text, utterance.priority.name, utterance.pan)
            if utterance.repeatable:
                self.last_spoken = utterance.text
            try:
                self.backend.speak(utterance)
            except Exception:
                logger.exception("speech backend failed on %r", utterance.text)
