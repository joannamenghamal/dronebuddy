package com.example.dronebuddyapp.voice

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

// Speech -> text with Android's built-in recognizer.
// start() on press, stop() on release; then onHeard() gets the guesses
// (or onFailed() if nothing was heard). Prefers the on-device recognizer
// so it works offline. Use it only on the main thread.
class SpeechListener(
    private val context: Context,
    // Guesses, best first; confidences is null when there are no real scores
    private val onHeard: (alternatives: List<String>, confidences: FloatArray?) -> Unit,
    // Listening failed, with a short reason for the log
    private val onFailed: (reason: String) -> Unit,
) {

    companion object {
        private const val TAG = "SpeechListener"
        private const val MAX_GUESSES = 5

        // False if the phone has no speech recognizer (some emulators)
        fun isAvailable(context: Context) = SpeechRecognizer.isRecognitionAvailable(context)
    }

    private var recognizer: SpeechRecognizer? = null
    private var listening = false

    // True when speech is recognised on the phone itself (no internet needed)
    val onDevice: Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(context)

    // Start listening (needs mic permission). False if the last press is still being recognised.
    fun start(): Boolean {
        if (listening) return false
        val r = recognizer ?: createRecognizer().also { recognizer = it }
        listening = true
        r.startListening(recognizerIntent())
        return true
    }

    // Stop listening; the result comes to onHeard() shortly after
    fun stop() {
        if (!listening) return
        recognizer?.stopListening()
    }

    // Stop without a result (e.g. user left the screen mid-press)
    fun cancel() {
        listening = false
        recognizer?.cancel()
    }

    // Free the recognizer when the screen closes
    fun destroy() {
        listening = false
        recognizer?.destroy()
        recognizer = null
    }

    private fun createRecognizer(): SpeechRecognizer {
        val r = if (onDevice && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
        } else {
            SpeechRecognizer.createSpeechRecognizer(context)
        }
        Log.i(TAG, if (onDevice) "using the on-device speech recognizer" else "using the default speech recognizer")
        r.setRecognitionListener(listener)
        return r
    }

    private fun recognizerIntent() = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US")
        putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, MAX_GUESSES)
        putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
        // Work offline (no signal outdoors)
        putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
        putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
    }

    private val listener = object : RecognitionListener {
        override fun onResults(results: Bundle?) {
            listening = false
            val guesses = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
            if (guesses.isEmpty()) {
                onFailed("nothing heard")
                return
            }
            onHeard(guesses, realScores(results?.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)))
        }

        override fun onError(error: Int) {
            listening = false
            onFailed(describe(error))
        }

        override fun onReadyForSpeech(params: Bundle?) = Unit
        override fun onBeginningOfSpeech() = Unit
        override fun onRmsChanged(rmsdB: Float) = Unit
        override fun onBufferReceived(buffer: ByteArray?) = Unit
        override fun onEndOfSpeech() = Unit
        override fun onPartialResults(partialResults: Bundle?) = Unit
        override fun onEvent(eventType: Int, params: Bundle?) = Unit
    }

    // All 0.0 / -1 scores mean "no score"; otherwise every command would look unsure
    private fun realScores(scores: FloatArray?): FloatArray? =
        if (scores == null || scores.all { it <= 0f }) null else scores

    private fun describe(error: Int): String = when (error) {
        SpeechRecognizer.ERROR_NO_MATCH -> "nothing recognised"
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "nothing heard"
        SpeechRecognizer.ERROR_AUDIO -> "microphone error"
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "no microphone permission"
        SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT ->
            "speech recognition needs the internet on this phone"
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "speech recognizer busy"
        SpeechRecognizer.ERROR_CLIENT -> "speech recognizer stopped"
        else -> "speech recognizer error $error"
    }
}
