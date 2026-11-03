package com.example.dronebuddyapp.bridge

import org.json.JSONObject

/**
 * Wire format for the Python <-> Android bridge WebSocket link, matching
 * DRONE_BRIDGE.md exactly. Kept dependency-free (org.json, already on
 * Android) rather than pulling in kotlinx.serialization, since the message
 * set is small and fixed.
 */

/** How urgent something spoken to the user is - see the `say` message. */
enum class SpeechPriority { NORMAL, URGENT }

sealed class BridgeMessage {

    data class FlightCommand(
        val forward: Double,
        val right: Double,
        val up: Double,
        val yaw: Double,
        val sentAtEpochMs: Long,
    ) : BridgeMessage()

    data class Telemetry(
        val battery: Int?,
        val connected: Boolean,
        val latitude: Double?,
        val longitude: Double?,
        val altitude: Double?,
        val heading: Double?,
        val velocityX: Double?,
        val velocityY: Double?,
        val velocityZ: Double?,
        val timestampEpochMs: Long,
    ) : BridgeMessage()

    data class Heartbeat(val sentAtEpochMs: Long) : BridgeMessage()

    data class EmergencyStop(val reason: String) : BridgeMessage()

    data class Ack(val forType: String, val ok: Boolean, val detail: String? = null) : BridgeMessage()

    /** Python -> Android: speak this to the user. pan -1 (left ear) .. +1 (right ear), volume 0 .. 1. */
    data class Say(
        val text: String,
        val priority: SpeechPriority,
        val pan: Float,
        val volume: Float,
    ) : BridgeMessage()

    /** Android -> Python: what the user said on the push-to-talk screen, as a command. */
    data class VoiceCommand(
        val command: String,
        val argument: String?,
        val heard: String,
        val confidence: Double,
    ) : BridgeMessage()
}

/**
 * Command validation happens here, not in the caller: a malformed or
 * out-of-range command must never reach VirtualStickManager, since that
 * manager has no bounds-checking of its own to fall back on.
 */
object ProtocolCodec {

    private const val AXIS_MIN = -1.0
    private const val AXIS_MAX = 1.0

    /** The voice commands Python understands (app/voice_commands.py) - names must match exactly. */
    val VOICE_COMMANDS = setOf("START_SESSION", "STOP_SESSION", "WHERE_IS", "REPEAT", "LOUDER", "QUIETER")

    fun decodeFlightCommand(json: JSONObject): BridgeMessage.FlightCommand? {
        val forward = json.optDouble("forward", Double.NaN)
        val right = json.optDouble("right", Double.NaN)
        val up = json.optDouble("up", Double.NaN)
        val yaw = json.optDouble("yaw", Double.NaN)
        val sentAt = json.optLong("sent_at_epoch_ms", -1L)

        val values = listOf(forward, right, up, yaw)
        if (values.any { it.isNaN() || it.isInfinite() }) return null
        if (values.any { it < AXIS_MIN || it > AXIS_MAX }) return null
        if (sentAt < 0) return null

        return BridgeMessage.FlightCommand(forward, right, up, yaw, sentAt)
    }

    fun encodeTelemetry(t: BridgeMessage.Telemetry): String {
        val json = JSONObject()
        json.put("type", "telemetry")
        json.put("battery", t.battery ?: JSONObject.NULL)
        json.put("connected", t.connected)
        json.put("latitude", t.latitude ?: JSONObject.NULL)
        json.put("longitude", t.longitude ?: JSONObject.NULL)
        json.put("altitude", t.altitude ?: JSONObject.NULL)
        json.put("heading", t.heading ?: JSONObject.NULL)
        json.put("velocity_x", t.velocityX ?: JSONObject.NULL)
        json.put("velocity_y", t.velocityY ?: JSONObject.NULL)
        json.put("velocity_z", t.velocityZ ?: JSONObject.NULL)
        json.put("timestamp_epoch_ms", t.timestampEpochMs)
        return json.toString()
    }

    fun encodeAck(a: BridgeMessage.Ack): String {
        val json = JSONObject()
        json.put("type", "ack")
        json.put("for_type", a.forType)
        json.put("ok", a.ok)
        if (a.detail != null) json.put("detail", a.detail)
        return json.toString()
    }

    fun encodeEmergencyStop(reason: String): String {
        val json = JSONObject()
        json.put("type", "emergency_stop")
        json.put("reason", reason)
        return json.toString()
    }

    /**
     * A malformed `say` is dropped rather than half-spoken; pan and volume outside
     * their ranges are clamped, since a slightly-off number is still worth saying.
     */
    fun decodeSay(json: JSONObject): BridgeMessage.Say? {
        val text = json.optString("text", "").trim()
        if (text.isEmpty()) return null

        val priority = when (json.optString("priority", "NORMAL")) {
            "NORMAL" -> SpeechPriority.NORMAL
            "URGENT" -> SpeechPriority.URGENT
            else -> return null
        }

        val pan = json.optDouble("pan", 0.0)
        val volume = json.optDouble("volume", 1.0)
        if (listOf(pan, volume).any { it.isNaN() || it.isInfinite() }) return null

        return BridgeMessage.Say(
            text = text,
            priority = priority,
            pan = pan.coerceIn(-1.0, 1.0).toFloat(),
            volume = volume.coerceIn(0.0, 1.0).toFloat(),
        )
    }

    /** Null for a command Python wouldn't understand, so it's never sent. */
    fun encodeVoiceCommand(v: BridgeMessage.VoiceCommand): String? {
        if (v.command !in VOICE_COMMANDS) return null
        val json = JSONObject()
        json.put("type", "voice_command")
        json.put("command", v.command)
        json.put("argument", v.argument ?: JSONObject.NULL)
        json.put("heard", v.heard)
        json.put("confidence", v.confidence)
        return json.toString()
    }

    fun messageType(json: JSONObject): String? =
        if (json.has("type")) json.getString("type") else null
}
