package com.example.dronebuddyapp.voice

import com.example.dronebuddyapp.bridge.ProtocolCodec
import com.example.dronebuddyapp.voice.VoiceCommandParser.Result
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Checks the commands we send are voice_command messages Python understands
class VoiceCommandBridgeTest {

    @Test
    fun ourCommandNamesAreExactlyTheOnesTheBridgeSends() {
        assertEquals(ProtocolCodec.VOICE_COMMANDS, CommandType.values().map { it.name }.toSet())
    }

    @Test
    fun everyCommandEncodes() {
        for (type in CommandType.values()) {
            val argument = if (type == CommandType.WHERE_IS) "cup" else null
            val encoded = ProtocolCodec.encodeVoiceCommand(VoiceCommand(type, argument).toBridgeMessage())
            assertNotNull("$type was not encoded", encoded)
        }
    }

    @Test
    fun whereIsMyMugBecomesTheContractExample() {
        val r = VoiceCommandParser.parse("where is my mug", confidence = 0.82f)
        val command = (r as Result.Recognized).command

        val json = JSONObject(ProtocolCodec.encodeVoiceCommand(command.toBridgeMessage())!!)

        assertEquals("voice_command", json.getString("type"))
        assertEquals("WHERE_IS", json.getString("command"))
        assertEquals("cup", json.getString("argument"))
        assertEquals("where is my mug", json.getString("heard"))
        assertEquals(0.82, json.getDouble("confidence"), 0.0001)
    }

    @Test
    fun commandsWithoutAnArgumentSendNull() {
        val command = (VoiceCommandParser.parse("louder") as Result.Recognized).command

        val json = JSONObject(ProtocolCodec.encodeVoiceCommand(command.toBridgeMessage())!!)

        assertEquals("LOUDER", json.getString("command"))
        assertTrue(json.isNull("argument"))
    }
}
