package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import android.graphics.Color
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
import kotlinx.coroutines.flow.observeOn
import kotlinx.coroutines.launch


class DroneManagerViewModel(
    appContext : Context
) : ViewModel() {

    val droneManager = DroneManager(appContext)

    val droneAppConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.appRegisterStatus.asLiveData()

    val droneConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.droneConnectionStatus.asLiveData()

    val droneInAirStatus : LiveData<Boolean> =
        droneManager.droneFlightKeys.droneInAirStatus.asLiveData()

    private var initializersRan = false

    // Put all things that need an initializer into this function
    private fun initializers() {
        droneManager.droneFlightKeys.initializer()
    }


    // Bridge to the Python side (see BRIDGE_INTEGRATION.md). The laptop connects to
    // this phone on BRIDGE_PORT; the bridge passes its commands to commandHandler,
    // which flies the drone, and sends telemetry and camera frames back.
    private val speechPlayer = SpeechPlayer(appContext)
    private val commandHandler = DjiCommandHandler(droneManager.virtualStick)

    private val _pythonConnectionStatus = MutableStateFlow(false)
    val pythonConnectionStatus: LiveData<Boolean> = _pythonConnectionStatus.asStateFlow().asLiveData()

    // Connected but nothing heard for 3s (laptop closed, frozen, out of Wi-Fi). The
    // socket itself can take a minute to notice that, so this is what hands the
    // drone back to the controller quickly.
    @Volatile private var pythonSilent = false

    // Same as commandHandler, plus updating pythonConnectionStatus and the log
    private val bridgeHandler = object : BridgeServer.Handler by commandHandler {
        override fun onClientConnected() {
            pythonSilent = false
            _pythonConnectionStatus.value = true
            bridgeLog("Python connected", LogItem.Status.INFO)
            commandHandler.onClientConnected()
            viewModelScope.launch { updateVirtualStick() }
        }

        override fun onClientDisconnected() {
            _pythonConnectionStatus.value = false
            bridgeLog("Python disconnected", LogItem.Status.WARNING)
            commandHandler.onClientDisconnected()
            viewModelScope.launch { updateVirtualStick() }
        }

        override fun onLinkLost() {
            pythonSilent = true
            bridgeLog("No messages from Python for 3s", LogItem.Status.WARNING)
            commandHandler.onLinkLost()
            viewModelScope.launch { updateVirtualStick() }
        }

        override fun onFlightCommand(command: BridgeMessage.FlightCommand) {
            if (pythonSilent) {
                // Python is back: hand the drone to it again
                pythonSilent = false
                bridgeLog("Python responding again", LogItem.Status.INFO)
                viewModelScope.launch { updateVirtualStick() }
            }
            commandHandler.onFlightCommand(command)
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
    private var virtualStickOn = false

    // Please use me instead of the virtualStickOn Variable! This is so UI can be dynamically updated
    // You need to set the below variable inside of the DjiVirtualStickController.kt file
    val virtualStickEnableStatus: LiveData<Boolean> = droneManager.virtualStick.virtualStickEnabledStatus.asLiveData()

    private val bridgeServer = BridgeServer(
        port = BRIDGE_PORT,
        handler = bridgeHandler,
        onSay = speechPlayer::speak,
        onListening = { bridgeLog("Bridge running, waiting for Python on port $BRIDGE_PORT", LogItem.Status.INFO) },
        onServerError = { e -> bridgeLog("Bridge failed to start: ${e.message}", LogItem.Status.ERROR) },
    )

    init {
        commandHandler.start()
        // Lets the server rebind its port straight away if the app is restarted
        bridgeServer.isReuseAddr = true
        bridgeServer.start()

        // The camera feed and telemetry need a connected aircraft (and an initialized SDK)
        viewModelScope.launch {
            droneManager.droneConnectionControl.droneConnectionStatus.collect { connected ->
                if (connected) startDroneFeeds() else stopDroneFeeds()
                updateVirtualStick()
            }


        }

        // Handle Initializing Initializers based on when the drone is connected
        viewModelScope.launch {
            droneManager.droneConnectionControl.droneConnectionStatus.collect { registered ->
                if (registered && !initializersRan) {
                    LogItem.addLog(
                        "Drone ViewModel",
                        "Drone Connected, Running Initializers",
                        LogItem.Status.INFO
                    )
                    initializers()
                    LogItem.addLog(
                        "Drone ViewModel",
                        "Drone Connected, Initializers Complete",
                        LogItem.Status.INFO
                    )
                    initializersRan = true
                }
                else if (!registered && initializersRan) {
                    LogItem.addLog("Drone ViewModel", "Drone Disconnected, Marking Initializers as Not Ran!", LogItem.Status.WARNING)
                    initializersRan = false
                }
                else if(registered && initializersRan) {
                    LogItem.addLog("Drone ViewModel", "Drone Connected, but already Initialized?", LogItem.Status.ERROR)
                }
                else {
                    LogItem.addLog("Drone ViewModel", "Drone Disconnected, but already Uninitialized? (Ignore if app just opened)", LogItem.Status.ERROR)
                }
            }   
        }
    }

    private fun startDroneFeeds() {
        if (droneFeedsRunning) return
        droneFeedsRunning = true
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
    }

    /**
     * Virtual stick is on only while both the drone and the laptop are connected
     * (and the laptop hasn't gone silent for 3s).
     * While it's on, the app flies the drone and the controller's sticks are ignored;
     * the rest of the time the controller flies it as normal. So the pilot can take
     * off by hand before starting the laptop program, and gets the sticks back the
     * moment the laptop program quits, or within 3s if the laptop goes silent.
     * Main thread only.
     */
    private fun updateVirtualStick() {
        val wanted = droneManager.droneConnectionControl.droneConnectionStatus.value &&
            _pythonConnectionStatus.value && !pythonSilent
        if (wanted == virtualStickOn) return
        virtualStickOn = wanted
        if (wanted) {
            droneManager.virtualStick.enable { success, error ->
                if (success) {
                    bridgeLog("Virtual stick on: the laptop is flying the drone", LogItem.Status.WARNING)
                } else {
                    bridgeLog("Enabling virtual stick failed: $error", LogItem.Status.ERROR)
                    // Try again on the next connection change
                    viewModelScope.launch { virtualStickOn = false }
                }
            }
        } else {
            droneManager.virtualStick.disable { _, _ -> }
            bridgeLog("Virtual stick off: the controller has the drone", LogItem.Status.INFO)
        }
    }

    override fun onCleared() {
        super.onCleared()
        bridgeServer.shutdownServer()
        commandHandler.stop()
        stopDroneFeeds()
        if (virtualStickOn) droneManager.virtualStick.disable { _, _ -> }
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