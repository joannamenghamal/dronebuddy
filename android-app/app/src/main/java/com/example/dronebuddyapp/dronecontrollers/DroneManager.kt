package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import dji.sampleV5.aircraft.visualbuddy.DBDroneFlightControl
import dji.sampleV5.aircraft.visualbuddy.DBDroneKeyControl


// so that it can be accissble everywhere as a singlton
class DroneManager(context: Context) {
    private val droneConnectionControl = DBDroneConnectionControl(context)
    private val droneFlightControl = DBDroneFlightControl()
    private val droneKeyControl = DBDroneKeyControl()


}