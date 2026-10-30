"""The two Visual Buddy audio messages on the bridge WebSocket, kept in this one file so
the format can change in one place.

    phone -> Python:  {"type": "voice_command", "command": "WHERE_IS", "argument": "cup",
                       "heard": "where is my mug", "confidence": 0.82}
    Python -> phone:  {"type": "say", "text": "Chair ahead", "priority": "URGENT",
                       "pan": -0.6, "volume": 0.8}

Not yet agreed with the bridge's owner, so DJIController does not send or receive them
yet; see DRONE_BRIDGE.md for the messages that exist today."""

from typing import Optional

from app.voice_commands import CommandType, VoiceCommand

VOICE_COMMAND_TYPE = "voice_command"
SAY_TYPE = "say"


def say_message(text, priority, pan=0.0, volume=1.0) -> dict:
    """Python -> phone: speak this. priority is an audio_output.Priority; pan is
    -1.0 (left ear) .. +1.0 (right ear); volume is 0.0 .. 1.0."""
    return {
        "type": SAY_TYPE,
        "text": text,
        "priority": priority.name,
        "pan": round(max(-1.0, min(1.0, pan)), 2),
        "volume": round(max(0.0, min(1.0, volume)), 2),
    }


def parse_voice_command(message: dict) -> Optional[VoiceCommand]:
    """Phone -> Python: the VoiceCommand in a bridge message, or None if the message
    isn't a well-formed voice_command (unknown commands are ignored, not fatal)."""
    if message.get("type") != VOICE_COMMAND_TYPE:
        return None

    try:
        command_type = CommandType(message["command"])
        confidence = float(message.get("confidence", 1.0))
    except (KeyError, ValueError, TypeError):
        return None

    argument = message.get("argument")
    return VoiceCommand(
        command_type,
        argument.lower() if isinstance(argument, str) else None,
        heard_text=str(message.get("heard", "")),
        confidence=confidence,
    )
