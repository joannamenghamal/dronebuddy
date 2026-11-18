package com.example.dronebuddyapp

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.HapticFeedbackConstants
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel
import com.example.dronebuddyapp.logcontent.LogItem
import com.example.dronebuddyapp.voice.SpeechListener
import com.example.dronebuddyapp.voice.VoiceCommandParser

// Push-to-talk screen: the whole screen is one button.
// Hold -> phone stops talking, vibrates, listens.
// Let go -> vibrates, finds the command, sends only the command to Python.
// TalkBack on: double-tap to start, double-tap again to stop.
class PushToTalkFragment : Fragment() {

    companion object {
        private const val TAG = "Push To Talk"
    }

    private val droneManagerViewModels: DroneManagerViewModel by activityViewModels()

    private lateinit var talkArea: View
    private lateinit var tvStatus: TextView
    private lateinit var tvHeard: TextView
    private var speechListener: SpeechListener? = null
    private var listening = false

    // Asks for the microphone the first time the screen is pressed
    private val askForMic = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            showIdle()
        } else {
            showMessage("Microphone permission is needed to talk to Drone Buddy")
            LogItem.addLog(TAG, "Microphone permission denied", LogItem.Status.ERROR)
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_push_to_talk, container, false)
    }

    @SuppressLint("ClickableViewAccessibility") // touches are handled; clicks still work for TalkBack
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        talkArea = view.findViewById(R.id.push_to_talk_area)
        tvStatus = view.findViewById(R.id.push_to_talk_status)
        tvHeard = view.findViewById(R.id.push_to_talk_heard)

        if (!SpeechListener.isAvailable(requireContext())) {
            showMessage("This phone has no speech recognizer")
            LogItem.addLog(TAG, "No speech recognizer on this phone", LogItem.Status.ERROR)
            return
        }

        speechListener = SpeechListener(
            context = requireContext(),
            onHeard = ::onHeard,
            onFailed = ::onListenError,
        )
        LogItem.addLog(
            TAG,
            if (speechListener?.onDevice == true) "Speech recognition: on the phone (works offline)"
            else "Speech recognition: phone default (may need internet)",
            LogItem.Status.INFO,
        )

        // Hold to talk (true = a touch is never also a click, so clicks are TalkBack only)
        talkArea.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> startListening()
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> stopListening()
            }
            true
        }

        // TalkBack: double-tap to start, double-tap again to stop
        talkArea.setOnClickListener {
            if (listening) stopListening() else startListening()
        }

        showIdle()
    }

    override fun onPause() {
        super.onPause()
        // Leaving the screen mid-press: drop it, send nothing
        if (listening) {
            listening = false
            speechListener?.cancel()
            showIdle()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        speechListener?.destroy()
        speechListener = null
    }

    private fun startListening() {
        val listener = speechListener ?: return
        if (listening) return

        if (!hasMicPermission()) {
            askForMic.launch(Manifest.permission.RECORD_AUDIO)
            return
        }

        // Still working out the last press
        if (!listener.start()) return

        // Stop any alert so the mic hears the user, not the phone
        droneManagerViewModels.stopSpeaking()
        talkArea.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)

        listening = true
        showListening()
    }

    private fun stopListening() {
        if (!listening) return
        listening = false
        talkArea.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
        speechListener?.stop()
        showMessage("…")
    }

    // Recognizer's guesses, best first -> command -> Python
    private fun onHeard(alternatives: List<String>, confidences: FloatArray?) {
        val heard = alternatives.first()

        when (val result = VoiceCommandParser.parseBest(alternatives, confidences)) {
            is VoiceCommandParser.Result.Recognized -> {
                val command = result.command
                val sent = droneManagerViewModels.sendVoiceCommand(command.toBridgeMessage())
                val what = command.type.name + (command.argument?.let { " $it" } ?: "")
                showHeard(command.heardText, if (sent) "Sent: $what" else "Not sent (laptop not connected): $what")
            }
            is VoiceCommandParser.Result.UnsupportedObject -> {
                showHeard(heard, "Can't look for \"${result.spokenObject}\"")
                LogItem.addLog(TAG, "Heard \"$heard\": YOLO can't detect ${result.spokenObject}", LogItem.Status.WARNING)
            }
            is VoiceCommandParser.Result.LowConfidence -> {
                showHeard(heard, "Not sure what was said, try again")
                LogItem.addLog(TAG, "Dropped unsure result \"$heard\" (${result.confidence})", LogItem.Status.INFO)
            }
            VoiceCommandParser.Result.NotACommand -> {
                showHeard(heard, "Not one of the commands")
                LogItem.addLog(TAG, "Heard \"$heard\": not a command", LogItem.Status.INFO)
            }
        }
    }

    private fun onListenError(reason: String) {
        listening = false
        showMessage(reason.replaceFirstChar { it.uppercase() })
        LogItem.addLog(TAG, "Listening failed: $reason", LogItem.Status.WARNING)
    }

    private fun hasMicPermission() =
        ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    // ---- What the screen shows ----

    private fun showIdle() {
        talkArea.setBackgroundColor(Color.parseColor("#E3F2FD"))
        tvStatus.setTextColor(Color.parseColor("#0D47A1"))
        tvStatus.text = "Hold anywhere to talk"
    }

    private fun showListening() {
        talkArea.setBackgroundColor(Color.parseColor("#2196F3"))
        tvStatus.setTextColor(Color.WHITE)
        tvStatus.text = "Listening…"
        tvHeard.text = ""
    }

    private fun showMessage(message: String) {
        talkArea.setBackgroundColor(Color.parseColor("#E3F2FD"))
        tvStatus.setTextColor(Color.parseColor("#0D47A1"))
        tvStatus.text = message
    }

    private fun showHeard(heard: String, outcome: String) {
        showIdle()
        tvHeard.text = "Heard: \"$heard\"\n$outcome"
    }
}
