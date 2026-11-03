package com.example.dronebuddyapp.audio

import com.example.dronebuddyapp.audio.SpeechPolicy.Action
import com.example.dronebuddyapp.bridge.SpeechPriority.NORMAL
import com.example.dronebuddyapp.bridge.SpeechPriority.URGENT
import org.junit.Assert.assertEquals
import org.junit.Test

/** When the phone cuts in, queues or drops what Python asks it to say. */
class SpeechPolicyTest {

    @Test
    fun normalAlertsQueueInOrder() {
        val policy = SpeechPolicy()

        assertEquals(Action.CUT_OFF_AND_SPEAK, policy.decide("1", URGENT))  // nothing playing: an urgent one just starts
        policy.finished("1")
        assertEquals(Action.QUEUE, policy.decide("2", NORMAL))
        assertEquals(Action.QUEUE, policy.decide("3", NORMAL))
        assertEquals(2, policy.pendingCount())
    }

    @Test
    fun urgentCutsOffNormalAndDropsTheStaleOnesWaiting() {
        val policy = SpeechPolicy()
        policy.decide("car", NORMAL)
        policy.decide("chair", NORMAL)

        assertEquals(Action.CUT_OFF_AND_SPEAK, policy.decide("approaching", URGENT))
        assertEquals(1, policy.pendingCount())
    }

    @Test
    fun urgentNeverCutsOffAnotherUrgent() {
        val policy = SpeechPolicy()
        policy.decide("approaching", URGENT)

        assertEquals(Action.QUEUE, policy.decide("answer", URGENT))
        assertEquals(2, policy.pendingCount())
    }

    @Test
    fun normalIsDroppedWhenSpeechFallsBehind() {
        val policy = SpeechPolicy(maxPending = 3)
        policy.decide("a", NORMAL)
        policy.decide("b", NORMAL)
        policy.decide("c", NORMAL)

        assertEquals(Action.DROP, policy.decide("d", NORMAL))
        assertEquals(3, policy.pendingCount())

        // ...but an urgent one still gets through
        assertEquals(Action.CUT_OFF_AND_SPEAK, policy.decide("approaching", URGENT))
    }

    @Test
    fun finishingOrStoppingFreesTheQueue() {
        val policy = SpeechPolicy(maxPending = 1)
        policy.decide("a", NORMAL)
        assertEquals(Action.DROP, policy.decide("b", NORMAL))

        policy.finished("a")
        assertEquals(Action.QUEUE, policy.decide("c", NORMAL))

        policy.stopped()  // push-to-talk pressed
        assertEquals(0, policy.pendingCount())
    }
}
