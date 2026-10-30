import time
from dataclasses import dataclass

from app.audio_output import Priority
from app.person_tracker import describe_position
from app.tracking_module import APPROACHING, LEFT_FRAME, NEW

ALERT_COOLDOWN_S = 5.0    # Don't repeat the same alert about the same person more often than this
MESSAGE_COOLDOWN_S = 2.0  # Don't say the exact same words twice in a row, even about different people


@dataclass
class Alert:
    text: str
    priority: Priority = Priority.NORMAL
    pan: float = 0.0  # Where the sound comes from: -1.0 = left ear .. +1.0 = right ear


class ComputeActions:
    """Decides which tracked-person activities are worth telling the user about,
    and turns them into short spoken alerts. Other activities (standing still,
    moving away...) are only logged, so the user isn't flooded with speech."""

    def __init__(self, cooldown_s=ALERT_COOLDOWN_S, message_cooldown_s=MESSAGE_COOLDOWN_S,
                 clock=time.monotonic):
        self.cooldown_s = cooldown_s
        self.message_cooldown_s = message_cooldown_s
        self.clock = clock
        self.last_alert = {}    # (track_id, activity) -> time it was last spoken
        self.last_message = {}  # message text -> time it was last spoken

    def compute(self, events):
        """events: ActivityEvents from the TrackingModule. Returns a list of Alerts."""
        now = self.clock()
        alerts = []

        for event in events:
            message = describe_event(event)
            if message is None:
                continue

            key = (event.track_id, event.activity)
            if now - self.last_alert.get(key, float("-inf")) < self.cooldown_s:
                continue

            ## Two people walking in together shouldn't produce "Person ahead, Person ahead"
            if now - self.last_message.get(message, float("-inf")) < self.message_cooldown_s:
                continue

            self.last_alert[key] = now
            self.last_message[message] = now

            ## Someone coming toward the user is urgent; the sound comes from their side
            priority = Priority.URGENT if event.activity == APPROACHING else Priority.NORMAL
            alerts.append(Alert(message, priority, max(-1.0, min(1.0, event.horizontal_error))))

        return alerts


def describe_event(event):
    position = describe_position(event.horizontal_error)

    if event.activity == APPROACHING:
        return f"Person approaching, {position}"
    elif event.activity == NEW:
        return f"Person {position}"
    elif event.activity == LEFT_FRAME:
        return "Person out of view"
    else:
        return None
