package com.example.dronebuddyapp.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import java.util.concurrent.Executors
import kotlin.math.PI
import kotlin.math.min
import kotlin.math.sin

/**
 * Plays Python's `tone` message: a short beep meaning "the person I just warned you
 * about is still coming closer". Stereo, so it comes from that person's side, like
 * the words did. Each tone is a few kilobytes of generated audio, played on its own
 * thread so the bridge's socket thread never waits.
 */
class TonePlayer(
    private val frequencyHz: Double = 880.0,
    private val durationMs: Int = 150,
) {
    companion object {
        private const val TAG = "TonePlayer"
        private const val SAMPLE_RATE = 44_100
        private const val FADE_MS = 10  // Fade in and out so the beep doesn't click
    }

    private val worker = Executors.newSingleThreadExecutor()

    /** pan -1 (left ear) .. +1 (right ear), volume 0 .. 1. Safe to call from any thread. */
    fun play(pan: Float, volume: Float) {
        worker.execute {
            try {
                playNow(pan, volume)
            } catch (e: Exception) {
                Log.w(TAG, "tone failed", e)
            }
        }
    }

    fun shutdown() {
        worker.shutdownNow()
    }

    private fun playNow(pan: Float, volume: Float) {
        val samples = toneSamples(frequencyHz, durationMs, pan, volume, SAMPLE_RATE, FADE_MS)
        val track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)  // Same volume knob as the spoken alerts
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
                    .build()
            )
            .setTransferMode(AudioTrack.MODE_STATIC)
            .setBufferSizeInBytes(samples.size * 2)
            .build()
        try {
            track.write(samples, 0, samples.size)
            track.play()
            Thread.sleep(durationMs + 50L)
        } finally {
            track.release()
        }
    }
}

/**
 * Interleaved stereo 16-bit samples (left, right, left, right...) of a sine beep.
 * The far ear gets less as pan moves away from it; the near ear stays at volume.
 * No Android dependency, so it's unit tested.
 */
internal fun toneSamples(
    frequencyHz: Double,
    durationMs: Int,
    pan: Float,
    volume: Float,
    sampleRate: Int,
    fadeMs: Int,
): ShortArray {
    val p = pan.coerceIn(-1f, 1f)
    val v = volume.coerceIn(0f, 1f)
    val leftGain = v * min(1f, 1f - p)
    val rightGain = v * min(1f, 1f + p)

    val frames = sampleRate * durationMs / 1000
    val fadeFrames = (sampleRate * fadeMs / 1000).coerceAtLeast(1)
    val out = ShortArray(frames * 2)
    for (i in 0 until frames) {
        val envelope = min(1.0, min(i, frames - 1 - i).toDouble() / fadeFrames)
        val s = sin(2 * PI * frequencyHz * i / sampleRate) * envelope * Short.MAX_VALUE * 0.8
        out[2 * i] = (s * leftGain).toInt().toShort()
        out[2 * i + 1] = (s * rightGain).toInt().toShort()
    }
    return out
}
