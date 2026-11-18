package com.example.dronebuddyapp.voice

import com.example.dronebuddyapp.bridge.BridgeMessage

// The 6 voice commands. Names must match app/voice_commands.py and
// ProtocolCodec.VOICE_COMMANDS in Protocol.kt (sent as plain strings).
enum class CommandType {
    START_SESSION,  // "start", "hey buddy"
    STOP_SESSION,   // "stop", "end session"
    WHERE_IS,       // "where is my cup" (argument = YOLO class name)
    REPEAT,         // "say again", "what?"
    LOUDER,         // "louder"
    QUIETER,        // "quieter"
}

// One command the user said on the push-to-talk screen
data class VoiceCommand(
    val type: CommandType,
    // WHERE_IS only: YOLO name like "cup"; null for other commands
    val argument: String? = null,
    // What speech-to-text heard (for the log)
    val heardText: String = "",
    // 0.0-1.0; 1.0 when the recognizer gives no score
    val confidence: Float = 1.0f,
) {
    // The voice_command message sent to Python over the bridge
    fun toBridgeMessage() = BridgeMessage.VoiceCommand(
        command = type.name,
        argument = argument,
        heard = heardText,
        confidence = confidence.toDouble(),
    )
}
