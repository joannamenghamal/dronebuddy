package com.example.dronebuddyapp.dronecontrollers

import com.example.dronebuddyapp.logcontent.LogItem
import dji.sdk.keyvalue.key.BatteryKey
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.sdk.keyvalue.value.common.Velocity3D
import dji.sdk.keyvalue.value.flightcontroller.CompassCalibrationState
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.pow
import kotlin.math.sqrt

// The point of this class is to allow any keys pertaining to flights to be instantiated here
// This is different from DBFlightControl since those controls the virtual sticks, which are not keys
// This is different from DBKeyControl since its the actual created keys instances
// onValueChange, p0 is oldValue and p1 is the newValue
class DBDroneFlightKeys(private val keyControl : DBDroneKeyControl) {
    private val _droneInAirStatus = MutableStateFlow(false)
    val droneInAirStatus : StateFlow<Boolean> = _droneInAirStatus.asStateFlow()
    private val _droneBatteryStatus = MutableStateFlow(-100)
    val droneBatteryStatus : StateFlow<Int> = _droneBatteryStatus.asStateFlow()
    private val _droneSpeedStatus = MutableStateFlow(0.0)
    val droneSpeedStatus : StateFlow<Double> = _droneSpeedStatus.asStateFlow()
    private val _droneAltitudeStatus = MutableStateFlow(0.0)
    val droneAltitudeStatus : StateFlow<Double> = _droneAltitudeStatus.asStateFlow()
    private val _droneCalibrationStatus = MutableStateFlow("")
    val droneCalibrationStatus : StateFlow<String> = _droneCalibrationStatus.asStateFlow()

    // This needs to be ran after a drone connection is made, and potentially re-ran everytime a
    // drone connection is remade
    fun initializer() {
        droneFlyingStatus()
        droneBatteryStatus()
        droneSpeedStatus()
        droneAltitudeStatus()
        droneCompassCalibrationStatus()
    }

    private fun droneFlyingStatus() {
        val callback = object: CommonCallbacks.KeyListener<Boolean> {
            override fun onValueChange(p0: Boolean?, p1: Boolean?) {
                if (p1 != null) {
                    _droneInAirStatus.value = p1
                    LogItem.addLog(
                        "Flight Keys",
                        "Drone Flight Status Changed! Is Now: $p1",
                        LogItem.Status.ERROR
                    )
                } else {
                    LogItem.addLog(
                        "Flight Keys",
                        "Could not get drone flying status",
                        LogItem.Status.ERROR
                    )
                }
            }

        }
        val key = keyControl.spawnKeyListeners(FlightControllerKey.KeyIsFlying, callback)
    }

    private fun droneBatteryStatus() {
        val callback = object: CommonCallbacks.KeyListener<Int> {
            override fun onValueChange(p0: Int?, p1: Int?) {
                if (p1 != null) {
                    _droneBatteryStatus.value = p1
                    LogItem.addLog(
                        "Flight Keys",
                        "Drone Battery Changed! Is Now: $p1",
                        LogItem.Status.ERROR
                    )
                } else {
                    _droneBatteryStatus.value = -100
                    LogItem.addLog(
                        "Flight Keys",
                        "Could not get drone battery status",
                        LogItem.Status.ERROR
                    )
                }
            }

        }
        val key = keyControl.spawnKeyListeners(BatteryKey.KeyChargeRemainingInPercent, callback)
    }

    private fun droneSpeedStatus() {
        val callback = object: CommonCallbacks.KeyListener<Velocity3D> {
            override fun onValueChange(p0: Velocity3D?, p1: Velocity3D?) {
                if (p1 != null) {
                    val xPow2 = p1.x.pow(2)
                    val yPow2 = p1.y.pow(2)
                    val zPow2 = p1.z.pow(2)
                    val calcSpeed = sqrt(xPow2 + yPow2 + zPow2)
                    _droneSpeedStatus.value = calcSpeed
                } else {
                    _droneSpeedStatus.value = -1.0
                    LogItem.addLog(
                        "Flight Keys",
                        "Could not get drone flying status",
                        LogItem.Status.ERROR
                    )
                }
            }

        }
        val key = keyControl.spawnKeyListeners(FlightControllerKey.KeyAircraftVelocity, callback)
    }

    private fun droneAltitudeStatus() {
        val callback = object: CommonCallbacks.KeyListener<Double> {
            override fun onValueChange(p0: Double?, p1: Double?) {
                if (p1 != null) {
                    _droneAltitudeStatus.value = p1
                } else {
                    _droneAltitudeStatus.value = -1.0
                    LogItem.addLog(
                        "Flight Keys",
                        "Could not get drone flying status",
                        LogItem.Status.ERROR
                    )
                }
            }

        }
        val key = keyControl.spawnKeyListeners(FlightControllerKey.KeyAltitude, callback)
    }

    private fun droneCompassCalibrationStatus() {
//        IDLE	Normal status. The compass is not calibrated.
//        HORIZONTAL	The horizontal calibration of the compass. The user should horizontally hold the aircraft and rotate it 360 degrees.
//        VERTICAL	The compass vertical calibration. The user should vertically hold the aircraft and rotate it 360 degrees.
//        SUCCEEDED	Compass calibration success.
//        FAILED	Compass calibration is failed. The user should make sure there are no magnets or metal objects near the aircraft and retry.
          val callback = object: CommonCallbacks.KeyListener<CompassCalibrationState> {
            override fun onValueChange(p0: CompassCalibrationState?, p1: CompassCalibrationState?) {
                if (p1 != null) {
                    if (p1 == CompassCalibrationState.IDLE) {
                        _droneCalibrationStatus.value = "IDLE"
                    }
                    else if (p1 == CompassCalibrationState.SUCCEEDED) {
                        _droneCalibrationStatus.value = "CALIBRATED!"
                    }
                    else if (p1 == CompassCalibrationState.FAILED) {
                        _droneCalibrationStatus.value = "FAILED! REDO CALIBRATION"
                    }
                    else if (p1 == CompassCalibrationState.UNKNOWN) {
                        _droneCalibrationStatus.value = "UNKNOWN STATE! REDO CALIBRATION"
                    }
                    else if (p1 == CompassCalibrationState.HORIZONTAL) {
                        _droneCalibrationStatus.value = "ROTATE HORIZONTALLY 360 DEGREES"
                    }
                    else if (p1 == CompassCalibrationState.VERTICAL) {
                        _droneCalibrationStatus.value = "ROTATE VERTICAL 360 DEGREES"
                    }
                } else {
                    _droneCalibrationStatus.value = "ERROR"
                    LogItem.addLog(
                        "Flight Keys",
                        "Could not get drone flying status",
                        LogItem.Status.ERROR
                    )
                }
            }

        }
        val key = keyControl.spawnKeyListeners(FlightControllerKey.KeyCompassCalibrationStatus, callback)
    }

    fun activateDroneLiftoff(successLambda : (() -> Unit)? = null, failLambda : ((IDJIError) -> Unit)? = null) {
        keyControl.performActionOnce(
            FlightControllerKey.KeyStartTakeoff,
            "Liftoff Activated",
            successLambda = { successLambda?.invoke() },
            failLambda = failLambda
        )
    }

    fun  activateDroneLanding(successLambda : (() -> Unit)? = null, failLambda : ((IDJIError) -> Unit)? = null) {
        keyControl.performActionOnce(
            FlightControllerKey.KeyStartAutoLanding,
            "Landing Activated",
            successLambda = { successLambda?.invoke() },
            failLambda = failLambda
        )
    }

}