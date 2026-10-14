package com.dronebuddy.bridge

import android.os.Bundle
import android.util.Log
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.dronebuddy.bridge.bridge.BridgeServer
import com.dronebuddy.bridge.dji.DjiCameraStreamProvider
import com.dronebuddy.bridge.dji.DjiSdkConnectionManager
import com.dronebuddy.bridge.dji.DjiTelemetryProvider
import com.dronebuddy.bridge.dji.DjiVirtualStickController
import com.dronebuddy.bridge.protocol.BridgeMessage

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
        // Must match app.config.Config.bridge_port's default (8765) in the
        // Python repo so a fresh checkout works with zero config on either
        // side - see DRONE_BRIDGE.md.
        private const val BRIDGE_PORT = 8765
    }

    private lateinit var sdkStatusText: TextView
    private lateinit var aircraftStatusText: TextView
    private lateinit var bridgeStatusText: TextView

    private var bridgeServer: BridgeServer? = null
    private val virtualStick = DjiVirtualStickController()
    private val telemetryProvider = DjiTelemetryProvider()
    private val cameraStreamProvider = DjiCameraStreamProvider()
    private lateinit var sdkConnectionManager: DjiSdkConnectionManager
    @Volatile private var aircraftConnected = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        sdkStatusText = findViewById(R.id.sdkStatusText)
        aircraftStatusText = findViewById(R.id.aircraftStatusText)
        bridgeStatusText = findViewById(R.id.bridgeStatusText)

        sdkConnectionManager = DjiSdkConnectionManager(applicationContext)
        sdkConnectionManager.statusListener = DjiSdkConnectionManager.StatusListener { status ->
            runOnUiThread { sdkStatusText.text = "SDK: $status" }
        }
        sdkConnectionManager.aircraftConnectionListener =
            DjiSdkConnectionManager.AircraftConnectionListener { connected ->
                aircraftConnected = connected
                runOnUiThread { aircraftStatusText.text = "Aircraft: ${if (connected) "connected" else "disconnected"}" }
                if (connected) {
                    virtualStick.enable { success, error ->
                        if (!success) {
                            Log.w(TAG, "enableVirtualStick failed: $error")
                        }
                    }
                } else {
                    virtualStick.disable { _, _ -> }
                }
            }

        sdkConnectionManager.registerAndInit()

        telemetryProvider.startListening { snapshot ->
            bridgeServer?.broadcastTelemetry(
                BridgeMessage.Telemetry(
                    battery = snapshot.battery,
                    connected = aircraftConnected,
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

        cameraStreamProvider.startListening { jpegBytes ->
            bridgeServer?.broadcastVideoFrame(jpegBytes)
        }

        startBridgeServer()
    }

    private fun startBridgeServer() {
        val server = BridgeServer(port = BRIDGE_PORT, virtualStick = virtualStick)
        bridgeServer = server
        server.start()
        bridgeStatusText.text = "Bridge: listening on $BRIDGE_PORT"
    }

    override fun onDestroy() {
        super.onDestroy()
        telemetryProvider.stopListening()
        cameraStreamProvider.stopListening()
        bridgeServer?.shutdownServer()
    }
}
