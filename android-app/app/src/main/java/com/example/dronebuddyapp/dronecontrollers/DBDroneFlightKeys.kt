package com.example.dronebuddyapp.dronecontrollers

import com.example.dronebuddyapp.logcontent.LogItem
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.v5.common.callback.CommonCallbacks
import dji.upgrade.UpgradeError
import dji.v5.common.error.IDJIError
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

// The point of this class is to allow any keys pertaining to flights to be instantiated here
// This is different from DBFlightControl since those controls the virtual sticks, which are not keys
// This is different from DBKeyControl since its the actual created keys instances
// onValueChange, p0 is oldValue and p1 is the newValue
class DBDroneFlightKeys(private val keyControl : DBDroneKeyControl) {
    private val _droneInAirStatus = MutableStateFlow(false)
    val droneInAirStatus : StateFlow<Boolean> = _droneInAirStatus.asStateFlow()

    // This needs to be ran after a drone connection is made, and potentially re-ran everytime a
    // drone connection is remade
    fun initializer() {
        droneFlyingStatus()
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