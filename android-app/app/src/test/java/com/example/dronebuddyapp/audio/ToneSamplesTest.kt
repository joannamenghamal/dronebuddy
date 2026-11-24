package com.example.dronebuddyapp.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/** The warning tone's generated audio: length, which ear, and no click at either end. */
class ToneSamplesTest {

    private fun loudest(samples: ShortArray, channel: Int): Int =
        samples.filterIndexed { i, _ -> i % 2 == channel }.maxOf { abs(it.toInt()) }

    @Test
    fun lengthIsTheDurationInStereoFrames() {
        val samples = toneSamples(880.0, 150, 0f, 1f, 44_100, 10)

        assertEquals(44_100 * 150 / 1000 * 2, samples.size)
    }

    @Test
    fun centeredToneIsEqualInBothEars() {
        val samples = toneSamples(880.0, 150, 0f, 1f, 44_100, 10)

        assertEquals(loudest(samples, 0), loudest(samples, 1))
    }

    @Test
    fun panLeftIsSilentInTheRightEar() {
        val samples = toneSamples(880.0, 150, -1f, 1f, 44_100, 10)

        assertTrue(loudest(samples, 0) > 20_000)
        assertEquals(0, loudest(samples, 1))
    }

    @Test
    fun volumeScalesTheTone() {
        val full = loudest(toneSamples(880.0, 150, 0f, 1f, 44_100, 10), 0)
        val half = loudest(toneSamples(880.0, 150, 0f, 0.5f, 44_100, 10), 0)

        assertEquals(full / 2.0, half.toDouble(), full * 0.02)
    }

    @Test
    fun startsAndEndsSilentSoItDoesNotClick() {
        val samples = toneSamples(880.0, 150, 0f, 1f, 44_100, 10)

        assertEquals(0, samples[0].toInt())
        assertEquals(0, samples[samples.size - 1].toInt())
    }
}
