package com.example.dronebuddyapp.dronecontrollers

import dji.sdk.keyvalue.key.FlightControllerKey
import dji.v5.common.error.IDJIError
import dji.v5.et.action
import dji.v5.et.create

/**
 * Takeoff/landing are DJIKey action calls, not virtual-stick input — a Mini 3
 * won't leave the ground from sendVirtualStickAdvancedParam alone. KeyStartTakeoff
 * / KeyStartAutoLanding (DJIActionKeyInfo<EmptyMsg, EmptyMsg> on
 * DJIFlightControllerKey) and the create()/action() call shape are confirmed via
 * javap against dji-sdk-v5-aircraft-provided:5.18.0 — not guessed.
 */
object DjiFlightActions {

    fun takeoff(onResult: (Boolean, IDJIError?) -> Unit) {
        FlightControllerKey.KeyStartTakeoff.create().action(
            { onResult(true, null) },
            { error -> onResult(false, error) },
        )
    }

    fun land(onResult: (Boolean, IDJIError?) -> Unit) {
        FlightControllerKey.KeyStartAutoLanding.create().action(
            { onResult(true, null) },
            { error -> onResult(false, error) },
        )
    }
}
