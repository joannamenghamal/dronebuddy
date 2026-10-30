package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import dji.sampleV5.aircraft.visualbuddy.DBDroneFlightControl
import dji.sampleV5.aircraft.visualbuddy.DBDroneKeyControl


// so that it can be accissble everywhere as a singlton
class DroneManager(context: Context) {
    val droneConnectionControl = DBDroneConnectionControl(context)
    val droneFlightControl = DBDroneFlightControl()
    val droneKeyControl = DBDroneKeyControl()

    // Used by the bridge to the Python side (set up in DroneManagerViewModel)
    val virtualStick = DjiVirtualStickController()
    val telemetry = DjiTelemetryProvider()
    val cameraStream = DjiCameraStreamProvider()

}