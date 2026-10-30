package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.asLiveData
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.lifecycle.viewModelScope
import com.example.dronebuddyapp.audio.SpeechPlayer
import com.example.dronebuddyapp.bridge.BridgeMessage
import com.example.dronebuddyapp.bridge.BridgeServer
import com.example.dronebuddyapp.logcontent.LogItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


class DroneManagerViewModel(
    appContext : Context
) : ViewModel() {

    val droneManager = DroneManager(appContext)

    val droneAppConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.appRegisterStatus.asLiveData()

    val droneConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.droneConnectionStatus.asLiveData()

    // Bridge to the Python side (see BRIDGE_INTEGRATION.md). The laptop connects to
    // this phone on BRIDGE_PORT; the bridge passes its commands to commandHandler,
    // which flies the drone, and sends telemetry and camera frames back.
    private val speechPlayer = SpeechPlayer(appContext)
    private val commandHandler = DjiCommandHandler(droneManager.virtualStick)

    private val _pythonConnectionStatus = MutableStateFlow(false)
    val pythonConnectionStatus: LiveData<Boolean> = _pythonConnectionStatus.asStateFlow().asLiveData()

    // Same as commandHandler, plus updating pythonConnectionStatus and the log
    private val bridgeHandler = object : BridgeServer.Handler by commandHandler {
        override fun onClientConnected() {
            _pythonConnectionStatus.value = true
            bridgeLog("Python connected", LogItem.Status.INFO)
            commandHandler.onClientConnected()
        }

        override fun onClientDisconnected() {
            _pythonConnectionStatus.value = false
            bridgeLog("Python disconnected", LogItem.Status.WARNING)
            commandHandler.onClientDisconnected()
        }

        override fun onLinkLost() {
            bridgeLog("No messages from Python for 3s", LogItem.Status.WARNING)
            commandHandler.onLinkLost()
        }

        override fun onEmergencyStop() {
            bridgeLog("Emergency stop from Python, hovering", LogItem.Status.ERROR)
            commandHandler.onEmergencyStop()
        }
    }

    // The bridge and DJI call back on their own threads, and LogItem must only be
    // used from the main thread (see ARCHITECTURE.md), so hop there first
    private fun bridgeLog(message: String, status: LogItem.Status) {
        viewModelScope.launch { LogItem.addLog(BRIDGE_TAG, message, status) }
    }

    // Only touched from viewModelScope (main thread)
    private var droneFeedsRunning = false

    private val bridgeServer = BridgeServer(
        port = BRIDGE_PORT,
        handler = bridgeHandler,
        onSay = speechPlayer::speak,
    )

    init {
        commandHandler.start()
        // Lets the server rebind its port straight away if the app is restarted
        bridgeServer.isReuseAddr = true
        bridgeServer.start()
        bridgeLog("Listening for Python on port $BRIDGE_PORT", LogItem.Status.INFO)

        // The camera feed and telemetry need a connected aircraft (and an initialized SDK)
        viewModelScope.launch {
            droneManager.droneConnectionControl.droneConnectionStatus.collect { connected ->
                if (connected) startDroneFeeds() else stopDroneFeeds()
            }
        }
    }

    private fun startDroneFeeds() {
        if (droneFeedsRunning) return
        droneFeedsRunning = true
        droneManager.virtualStick.enable { success, error ->
            if (!success) bridgeLog("Enabling virtual stick failed: $error", LogItem.Status.ERROR)
        }
        droneManager.cameraStream.startListening { jpegBytes ->
            bridgeServer.sendVideoFrame(jpegBytes)
        }
        droneManager.telemetry.startListening { snapshot ->
            bridgeServer.sendTelemetry(
                BridgeMessage.Telemetry(
                    battery = snapshot.battery,
                    connected = droneManager.droneConnectionControl.droneConnectionStatus.value,
                    latitude = snapshot.latitude,
                    longitude = snapshot.longitude,
                    altitude = snapshot.altitude,
                    heading = snapshot.heading,
                    velocityX = snapshot.velocityX,
                    velocityY = snapshot.velocityY,
                    velocityZ = snapshot.velocityZ,
                    timestampEpochMs = System.currentTimeMillis(),
                )
            )
        }
    }

    private fun stopDroneFeeds() {
        // The status starts out false, before the SDK is even initialized
        if (!droneFeedsRunning) return
        droneFeedsRunning = false
        droneManager.cameraStream.stopListening()
        droneManager.telemetry.stopListening()
        droneManager.virtualStick.disable { _, _ -> }
    }

    override fun onCleared() {
        super.onCleared()
        bridgeServer.shutdownServer()
        commandHandler.stop()
        stopDroneFeeds()
        speechPlayer.shutdown()
    }


    // Factory as a companion object
    companion object {
        // Must match app.config.Config.bridge_port's default on the Python side
        private const val BRIDGE_PORT = 8765
        private const val BRIDGE_TAG = "Python Bridge"

        val appContextKey = CreationExtras.Key<Context>()

        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val appContext = checkNotNull(this[appContextKey])
                DroneManagerViewModel(
                    appContext = appContext
                )
            }
        }
    }
}