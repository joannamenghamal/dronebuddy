import json
import os
from datetime import datetime

## logs/ folder at the project root (next to app/)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


class SessionLogger:
    """Writes a timestamped log of everything that happens in a session, for caregiver review.

    One JSON object per line (JSON Lines), written and flushed as each event happens,
    so the log survives even if the program crashes."""

    def __init__(self, log_dir=LOG_DIR):
        os.makedirs(log_dir, exist_ok=True)

        started = datetime.now()
        self.path = os.path.join(log_dir, f"session_{started:%Y%m%d_%H%M%S}.jsonl")
        self.file = open(self.path, "w", encoding="utf-8")
        self.event_count = 0

    def log(self, event, **details):
        record = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
            **details,
        }
        self.file.write(json.dumps(record) + "\n")
        self.file.flush()
        self.event_count += 1

    def close(self):
        """Logs the session end and saves the file. Returns the log path."""
        self.log("session_end", total_events=self.event_count)
        self.file.close()
        return self.path
