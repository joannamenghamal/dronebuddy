package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import com.example.dronebuddyapp.dronecontrollers.DBDroneFlightControl
import com.example.dronebuddyapp.dronecontrollers.DBDroneKeyControl
import com.example.dronebuddyapp.dronecontrollers.DBDroneConnectionControl

// so that it can be accissble everywhere as a singlton
class DroneManager(context: Context) {
    val droneConnectionControl = DBDroneConnectionControl(context)
    val droneFlightControl = DBDroneFlightControl()
    val droneKeyControl = DBDroneKeyControl()
    val droneVideoManagerControl = DBDroneCameraStreamControl()
    val droneFlightKeys = DBDroneFlightKeys(droneKeyControl)

    // Used by the bridge to the Python side (set up in DroneManagerViewModel)
    val virtualStick = DjiVirtualStickController()
    val telemetry = DjiTelemetryProvider()
    val cameraStream = DjiCameraStreamProvider()

}