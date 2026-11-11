package com.example.dronebuddyapp.audio

import com.example.dronebuddyapp.bridge.SpeechPriority

/**
 * Decides what happens to each incoming `say`, with no Android dependency so it can
 * be unit tested. Same rules as the Python side (app/audio_output.py), applied where
 * the user actually hears them:
 *  - an URGENT alert cuts off a NORMAL one that's playing, and drops the NORMAL ones
 *    still waiting - they're stale by the time the urgent one finishes
 *  - an URGENT alert never cuts off another URGENT one; it waits its turn
 *  - a NORMAL alert is dropped when maxPending are already playing or waiting,
 *    because a stale warning is worse than none
 *
 * Thread-safe: BridgeServer calls decide() from its socket thread, TextToSpeech calls
 * finished() from its own.
 */
class SpeechPolicy(private val maxPending: Int = 3) {

    enum class Action { CUT_OFF_AND_SPEAK, QUEUE, DROP }

    /** Utterance id -> priority, in speaking order; the first one is playing (or about to). */
    private val pending = LinkedHashMap<String, SpeechPriority>()

    @Synchronized
    fun decide(id: String, priority: SpeechPriority): Action {
        val playing = pending.values.firstOrNull()
        val action = when {
            priority == SpeechPriority.URGENT && playing != SpeechPriority.URGENT -> Action.CUT_OFF_AND_SPEAK
            priority == SpeechPriority.NORMAL && pending.size >= maxPending -> Action.DROP
            else -> Action.QUEUE
        }
        when (action) {
            Action.CUT_OFF_AND_SPEAK -> {
                pending.clear()
                pending[id] = priority
            }
            Action.QUEUE -> pending[id] = priority
            Action.DROP -> Unit
        }
        return action
    }

    /** An utterance finished, failed or was cut off. */
    @Synchronized
    fun finished(id: String) {
        pending.remove(id)
    }

    /** Everything was stopped, e.g. the push-to-talk screen was pressed. */
    @Synchronized
    fun stopped() {
        pending.clear()
    }

    @Synchronized
    fun pendingCount(): Int = pending.size
}
