package com.dronebuddy.bridge.audio

import android.content.Context
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import com.dronebuddy.bridge.protocol.BridgeMessage
import java.util.Locale
import java.util.concurrent.atomic.AtomicLong

/**
 * Speaks Python's `say` messages to the visually impaired user with Android's
 * text-to-speech: URGENT alerts cut in (see SpeechPolicy), `pan` places the voice in
 * the left or right ear, `volume` follows LOUDER / QUIETER.
 *
 * The engine starts asynchronously; the first few messages that arrive before it's
 * ready (e.g. "Visual Buddy ready") are held and spoken once it is.
 */
class SpeechPlayer(
    context: Context,
    private val locale: Locale = Locale.US,
) : TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "SpeechPlayer"
        private const val MAX_HELD_BEFORE_READY = 3
    }

    private val policy = SpeechPolicy()
    private val nextId = AtomicLong()
    private val heldBeforeReady = ArrayDeque<BridgeMessage.Say>()  // guarded by itself
    @Volatile private var ready = false
    private val tts = TextToSpeech(context.applicationContext, this)

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            Log.e(TAG, "text-to-speech failed to start (status $status); alerts will not be spoken")
            return
        }

        val language = tts.setLanguage(locale)
        if (language == TextToSpeech.LANG_MISSING_DATA || language == TextToSpeech.LANG_NOT_SUPPORTED) {
            Log.w(TAG, "text-to-speech has no voice for $locale; using the engine's default")
        }

        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String) = Unit
            override fun onDone(utteranceId: String) = policy.finished(utteranceId)
            override fun onStop(utteranceId: String, interrupted: Boolean) = policy.finished(utteranceId)
            override fun onError(utteranceId: String, errorCode: Int) = policy.finished(utteranceId)

            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String) = policy.finished(utteranceId)
        })

        val held = synchronized(heldBeforeReady) {
            ready = true
            heldBeforeReady.toList().also { heldBeforeReady.clear() }
        }
        held.forEach { speak(it) }
    }

    /** Speaks a `say` message. Safe to call from any thread (BridgeServer calls it from its socket thread). */
    fun speak(say: BridgeMessage.Say) {
        synchronized(heldBeforeReady) {
            if (!ready) {
                if (heldBeforeReady.size < MAX_HELD_BEFORE_READY) heldBeforeReady.addLast(say)
                return
            }
        }

        val id = "say-${nextId.incrementAndGet()}"
        when (policy.decide(id, say.priority)) {
            SpeechPolicy.Action.CUT_OFF_AND_SPEAK -> enqueue(say, id, TextToSpeech.QUEUE_FLUSH)
            SpeechPolicy.Action.QUEUE -> enqueue(say, id, TextToSpeech.QUEUE_ADD)
            SpeechPolicy.Action.DROP -> Log.i(TAG, "dropped stale alert: ${say.text}")
        }
    }

    /**
     * Stops speaking at once. The push-to-talk screen calls this when it's pressed,
     * so the microphone hears the user and not the last alert.
     */
    fun stopSpeaking() {
        policy.stopped()
        tts.stop()
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }

    private fun enqueue(say: BridgeMessage.Say, id: String, queueMode: Int) {
        val params = Bundle().apply {
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, say.volume)
            putFloat(TextToSpeech.Engine.KEY_PARAM_PAN, say.pan)
        }
        if (tts.speak(say.text, queueMode, params, id) != TextToSpeech.SUCCESS) {
            policy.finished(id)
            Log.w(TAG, "text-to-speech refused: ${say.text}")
        }
    }
}
