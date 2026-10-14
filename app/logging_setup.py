import logging

# Every subsystem logs under this namespace (dronebuddy.drone.*, .safety,
# .detection, .tracking, .commands) so log level/output can be controlled
# for the whole app in one place, and so a log line's origin is legible from
# its logger name alone.
ROOT_LOGGER_NAME = "dronebuddy"


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)-28s %(message)s",
    )
    # Never log credentials/tokens: if a future DJI bridge client logs auth
    # headers or API keys for debugging, that must go through redaction, not
    # this logger directly.
    logging.getLogger(ROOT_LOGGER_NAME).setLevel(level)
