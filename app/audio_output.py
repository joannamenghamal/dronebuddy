import queue
import threading

MAX_PENDING = 3  # Old alerts are dropped if speech falls behind - stale cues are worse than none


class AudioOutput:
    """Speaks alerts to the user with offline text-to-speech (pyttsx3).

    Speech runs on a background thread so the video loop never waits for it.
    If pyttsx3 isn't available, alerts are only printed."""

    def __init__(self, rate=180):
        self.rate = rate
        self.pending = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def say(self, text):
        ## Keep the queue short so the user always hears what's happening *now*
        while self.pending.qsize() >= MAX_PENDING:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                break

        self.pending.put(text)

    def close(self, timeout_s=5.0):
        """Finishes speaking what's queued (e.g. "Session ended"), then stops."""
        self.pending.put(None)
        self.thread.join(timeout_s)

    def _run(self):
        ## The speech engine must be created on the thread that uses it
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
        except Exception as error:
            print(f"[AUDIO] Text-to-speech unavailable ({error}), printing alerts only")
            engine = None

        while True:
            text = self.pending.get()
            if text is None:
                break

            print(f"[AUDIO] {text}")
            if engine is not None:
                engine.say(text)
                engine.runAndWait()
