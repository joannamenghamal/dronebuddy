package com.example.dronebuddyapp.bridge

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The `say` / `voice_command` wire format, matching DRONE_BRIDGE.md and app/bridge_messages.py. */
class AudioProtocolTest {

    @Test
    fun decodesASayFromPython() {
        val say = ProtocolCodec.decodeSay(
            JSONObject("""{"type": "say", "text": "Chair ahead", "priority": "URGENT", "pan": -0.6, "volume": 0.8}""")
        )

        assertEquals(BridgeMessage.Say("Chair ahead", SpeechPriority.URGENT, -0.6f, 0.8f), say)
    }

    @Test
    fun missingPriorityPanAndVolumeGetSafeDefaults() {
        val say = ProtocolCodec.decodeSay(JSONObject("""{"type": "say", "text": "Person ahead"}"""))

        assertEquals(BridgeMessage.Say("Person ahead", SpeechPriority.NORMAL, 0f, 1f), say)
    }

    @Test
    fun panAndVolumeOutOfRangeAreClamped() {
        val say = ProtocolCodec.decodeSay(JSONObject("""{"type": "say", "text": "x", "pan": -3.0, "volume": 7}"""))!!

        assertEquals(-1f, say.pan, 0f)
        assertEquals(1f, say.volume, 0f)
    }

    @Test
    fun emptyTextOrUnknownPriorityIsDropped() {
        assertNull(ProtocolCodec.decodeSay(JSONObject("""{"type": "say", "text": "   "}""")))
        assertNull(ProtocolCodec.decodeSay(JSONObject("""{"type": "say", "priority": "URGENT"}""")))
        assertNull(ProtocolCodec.decodeSay(JSONObject("""{"type": "say", "text": "x", "priority": "LOUD"}""")))
    }

    @Test
    fun encodesAVoiceCommandForPython() {
        val encoded = ProtocolCodec.encodeVoiceCommand(
            BridgeMessage.VoiceCommand("WHERE_IS", "cup", "where is my mug", 0.82)
        )!!

        val json = JSONObject(encoded)
        assertEquals("voice_command", json.getString("type"))
        assertEquals("WHERE_IS", json.getString("command"))
        assertEquals("cup", json.getString("argument"))
        assertEquals("where is my mug", json.getString("heard"))
        assertEquals(0.82, json.getDouble("confidence"), 1e-9)
    }

    @Test
    fun noArgumentIsSentAsJsonNull() {
        val json = JSONObject(ProtocolCodec.encodeVoiceCommand(BridgeMessage.VoiceCommand("REPEAT", null, "say again", 0.9))!!)

        assertTrue(json.isNull("argument"))
    }

    @Test
    fun aCommandPythonDoesNotKnowIsNeverEncoded() {
        assertNull(ProtocolCodec.encodeVoiceCommand(BridgeMessage.VoiceCommand("DANCE", null, "dance", 0.9)))
    }

    @Test
    fun commandNamesMatchPython() {
        // Must stay identical to CommandType in app/voice_commands.py
        assertEquals(
            setOf("START_SESSION", "STOP_SESSION", "WHERE_IS", "REPEAT", "LOUDER", "QUIETER"),
            ProtocolCodec.VOICE_COMMANDS,
        )
    }
}
