package com.example.dronebuddyapp.voice

import com.example.dronebuddyapp.voice.VoiceCommandParser.Result
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Tests for heard text -> command. Run: right-click this file -> Run
class VoiceCommandParserTest {

    // Helpers --------------------

    private fun command(text: String, confidence: Float = 1.0f): VoiceCommand {
        val r = VoiceCommandParser.parse(text, confidence)
        assertTrue("expected a command for '$text' but got $r", r is Result.Recognized)
        return (r as Result.Recognized).command
    }

    private fun assertCommand(text: String, type: CommandType, argument: String? = null) {
        val c = command(text)
        assertEquals("type for '$text'", type, c.type)
        assertEquals("argument for '$text'", argument, c.argument)
        assertEquals("heard text is kept for the log", text, c.heardText)
    }

    private fun assertNotACommand(text: String) {
        assertEquals("'$text' should be ignored", Result.NotACommand, VoiceCommandParser.parse(text))
    }

    // The example phrases from the interface contract 
    @Test fun contractExamplePhrases() {
        assertCommand("start", CommandType.START_SESSION)
        assertCommand("hey buddy", CommandType.START_SESSION)
        assertCommand("stop", CommandType.STOP_SESSION)
        assertCommand("end session", CommandType.STOP_SESSION)
        assertCommand("where is my cup", CommandType.WHERE_IS, "cup")
        assertCommand("find the chair", CommandType.WHERE_IS, "chair")
        assertCommand("say again", CommandType.REPEAT)
        assertCommand("what?", CommandType.REPEAT)
        assertCommand("louder", CommandType.LOUDER)
        assertCommand("quieter", CommandType.QUIETER)
    }

    @Test fun planExampleMugMapsToCup() {
        // "where is my mug" -> WHERE_IS, cup  (step 3 of the plan)
        assertCommand("where is my mug", CommandType.WHERE_IS, "cup")
    }

    @Test fun planExampleBagMapsToBackpack() {
        assertCommand("where is my bag", CommandType.WHERE_IS, "backpack")
    }

    // How real recognizers write things 

    @Test fun capitalsPunctuationAndContractions() {
        assertCommand("Where's my CUP?", CommandType.WHERE_IS, "cup")
        assertCommand("Stop.", CommandType.STOP_SESSION)
        assertCommand("  LOUDER!!  ", CommandType.LOUDER)
        assertCommand("Where’s the chair", CommandType.WHERE_IS, "chair") // curly apostrophe
    }

    @Test fun politeAndFillerWords() {
        assertCommand("stop please", CommandType.STOP_SESSION)
        assertCommand("um louder", CommandType.LOUDER)
        assertCommand("okay say that again", CommandType.REPEAT)
        assertCommand("can you find my phone", CommandType.WHERE_IS, "cell phone")
        assertCommand("help me find the bottle", CommandType.WHERE_IS, "bottle")
    }

    @Test fun otherWhereIsPhrasings() {
        assertCommand("look for the laptop", CommandType.WHERE_IS, "laptop")
        assertCommand("where did i put my backpack", CommandType.WHERE_IS, "backpack")
        assertCommand("is there a person", CommandType.WHERE_IS, "person")
        assertCommand("is there an apple", CommandType.WHERE_IS, "apple")
        assertCommand("locate the dog", CommandType.WHERE_IS, "dog")
    }

    // Object names -> YOLO class names -------

    @Test fun multiWordYoloClasses() {
        assertCommand("find the stop sign", CommandType.WHERE_IS, "stop sign")
        assertCommand("where is the dining table", CommandType.WHERE_IS, "dining table")
        assertCommand("where is my cell phone", CommandType.WHERE_IS, "cell phone")
        assertCommand("find the traffic light", CommandType.WHERE_IS, "traffic light")
    }

    @Test fun synonyms() {
        assertEquals("cell phone", VoiceCommandParser.toYoloClass("phone"))
        assertEquals("dining table", VoiceCommandParser.toYoloClass("table"))
        assertEquals("couch", VoiceCommandParser.toYoloClass("sofa"))
        assertEquals("tv", VoiceCommandParser.toYoloClass("television"))
        assertEquals("refrigerator", VoiceCommandParser.toYoloClass("fridge"))
        assertEquals("person", VoiceCommandParser.toYoloClass("someone"))
        assertEquals("cup", VoiceCommandParser.toYoloClass("my red coffee mug"))
    }

    @Test fun plurals() {
        assertEquals("chair", VoiceCommandParser.toYoloClass("chairs"))
        assertEquals("knife", VoiceCommandParser.toYoloClass("knives"))
        assertEquals("bus", VoiceCommandParser.toYoloClass("buses"))
        assertEquals("vase", VoiceCommandParser.toYoloClass("vases"))
        assertEquals("bench", VoiceCommandParser.toYoloClass("benches"))
        assertEquals("wine glass", VoiceCommandParser.toYoloClass("glasses"))
        assertEquals("skis", VoiceCommandParser.toYoloClass("skis"))
        assertEquals("teddy bear", VoiceCommandParser.toYoloClass("teddy bears"))
        assertEquals("person", VoiceCommandParser.toYoloClass("people"))
    }

    @Test fun everyArgumentIsARealYoloClass() {
        // Contract: WHERE_IS arguments must be YOLO class names.
        val samples = listOf("mug", "bag", "phone", "table", "sofa", "fridge", "chairs", "people", "glasses")
        for (s in samples) {
            val label = VoiceCommandParser.toYoloClass(s)
            assertTrue("$s -> $label is not a YOLO class", label in VoiceCommandParser.YOLO_CLASSES)
        }
    }

    // Things YOLO can't see -------

    @Test fun unsupportedObjectsAreNotSentAsWhereIs() {
        val r = VoiceCommandParser.parse("where are my keys")
        assertTrue(r is Result.UnsupportedObject)
        assertEquals("keys", (r as Result.UnsupportedObject).spokenObject)

        assertTrue(VoiceCommandParser.parse("find my wallet") is Result.UnsupportedObject)
        assertTrue(VoiceCommandParser.parse("where is the door") is Result.UnsupportedObject)
        assertNull(VoiceCommandParser.toYoloClass("keys"))
    }

    // Must NOT trigger -----------

    @Test fun stopInsideASentenceDoesNotStopTheSession() {
        // The reason short commands must be the whole utterance.
        assertCommand("where is the stop sign", CommandType.WHERE_IS, "stop sign")
        assertNotACommand("i will stop by the store later")
        assertNotACommand("dont stop")
        assertNotACommand("the end of the street")
    }

    @Test fun ordinarySpeechIsIgnored() {
        assertNotACommand("")
        assertNotACommand("   ")
        assertNotACommand("[unk]")
        assertNotACommand("nice weather today")
        assertNotACommand("what time is it")
        assertNotACommand("find")          // no object
        assertNotACommand("where is the")  // no object
    }

    // Confidence -------------------

    @Test fun lowConfidenceIsDropped() {
        val r = VoiceCommandParser.parse("stop", confidence = 0.2f)
        assertTrue(r is Result.LowConfidence)
        assertEquals(0.2f, (r as Result.LowConfidence).confidence, 0.0001f)
    }

    @Test fun confidenceIsKeptOnTheCommand() {
        assertEquals(0.82f, command("where is my mug", 0.82f).confidence, 0.0001f)
    }

    @Test fun missingConfidenceCountsAsSure() {
        // On-device recognizers often report -1 / no score.
        assertEquals(1.0f, command("louder", -1f).confidence, 0.0001f)
    }

    @Test fun lowConfidenceNonCommandIsStillNotACommand() {
        assertEquals(Result.NotACommand, VoiceCommandParser.parse("nice weather", 0.1f))
    }

    // Several recognizer guesses 

    @Test fun parseBestUsesFirstGuessThatIsACommand() {
        val r = VoiceCommandParser.parseBest(
            listOf("where is my cap", "wear is my cup", "where is my cup"),
            floatArrayOf(0.6f, 0.5f, 0.4f),
            minConfidence = 0.3f,
        )
        assertTrue(r is Result.Recognized)
        val c = (r as Result.Recognized).command
        assertEquals(CommandType.WHERE_IS, c.type)
        assertEquals("cup", c.argument)
        assertEquals("where is my cup", c.heardText)
    }

    @Test fun parseBestWithoutConfidences() {
        val r = VoiceCommandParser.parseBest(listOf("hello", "louder"))
        assertEquals(CommandType.LOUDER, (r as Result.Recognized).command.type)
    }

    @Test fun parseBestReportsUnsupportedWhenNothingBetter() {
        val r = VoiceCommandParser.parseBest(listOf("where are my keys", "where are my peas"))
        assertTrue(r is Result.UnsupportedObject)
    }

    @Test fun parseBestNothingRecognized() {
        assertEquals(Result.NotACommand, VoiceCommandParser.parseBest(emptyList()))
        assertEquals(Result.NotACommand, VoiceCommandParser.parseBest(listOf("hello", "goodbye world")))
    }

    // Contract names must match Python exactly 

    @Test fun commandNamesMatchPythonContract() {
        assertEquals(
            listOf("START_SESSION", "STOP_SESSION", "WHERE_IS", "REPEAT", "LOUDER", "QUIETER"),
            CommandType.values().map { it.name },
        )
    }
}
