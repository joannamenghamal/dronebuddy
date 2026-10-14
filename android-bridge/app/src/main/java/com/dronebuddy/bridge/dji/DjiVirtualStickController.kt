package com.dronebuddy.bridge.dji

import android.util.Log
import dji.sdk.keyvalue.value.flightcontroller.FlightCoordinateSystem
import dji.sdk.keyvalue.value.flightcontroller.RollPitchControlMode
import dji.sdk.keyvalue.value.flightcontroller.VerticalControlMode
import dji.sdk.keyvalue.value.flightcontroller.VirtualStickFlightControlParam
import dji.sdk.keyvalue.value.flightcontroller.YawControlMode
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.aircraft.virtualstick.VirtualStickManager
import kotlin.math.max
import kotlin.math.min

/**
 * Wraps VirtualStickManager for velocity-mode flight control. Every DJI
 * type/method/field used below was confirmed via javap against the real
 * classes in dji-sdk-v5-aircraft(-provided):5.18.0 — not guessed:
 *  - VirtualStickManager.getInstance().enableVirtualStick/disableVirtualStick/
 *    setVirtualStickAdvancedModeEnabled/sendVirtualStickAdvancedParam
 *  - VirtualStickFlightControlParam's settable Double fields pitch/roll/yaw/
 *    verticalThrottle, plus its four control-mode enum fields
 *  - dji.v5.manager.aircraft.virtualstick.VirtualStickRange's published
 *    ceilings: roll/pitch velocity ±23 m/s, vertical velocity ±6 m/s, yaw
 *    angular velocity ±100 deg/s
 *
 * This project uses VELOCITY mode for roll/pitch/vertical and
 * ANGULAR_VELOCITY for yaw (rather than DJI's sample app's ANGLE default for
 * roll/pitch) because app/drone/controller.py's MovementCommand is defined
 * in terms of speed fractions, not tilt angles — see ARCHITECTURE.md.
 *
 * MAX_*_MPS / MAX_YAW_RATE_DEG_S below are this project's own conservative
 * ground-testing caps (not DJI facts), deliberately far inside the
 * VirtualStickRange ceilings; raise them only after verifying behavior per
 * TESTING.md. The clamp against VirtualStickRange itself is a hard backstop
 * so a bad MAX_* value here can never exceed what the SDK will accept.
 */
class DjiVirtualStickController {

    companion object {
        private const val TAG = "DjiVirtualStick"

        private const val MAX_HORIZONTAL_SPEED_MPS = 2.0
        private const val MAX_VERTICAL_SPEED_MPS = 1.0
        private const val MAX_YAW_RATE_DEG_S = 30.0

        private const val ROLL_PITCH_VELOCITY_CEILING = 23.0
        private const val VERTICAL_VELOCITY_CEILING = 6.0
        private const val YAW_ANGULAR_VELOCITY_CEILING = 100.0
    }

    private fun clamp(value: Double, ceiling: Double): Double =
        max(-ceiling, min(ceiling, value))

    fun enable(onResult: (Boolean, IDJIError?) -> Unit) {
        Log.i(TAG, "enabling virtual stick")
        VirtualStickManager.getInstance().enableVirtualStick(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                VirtualStickManager.getInstance().setVirtualStickAdvancedModeEnabled(true)
                onResult(true, null)
            }

            override fun onFailure(error: IDJIError) {
                onResult(false, error)
            }
        })
    }

    fun disable(onResult: (Boolean, IDJIError?) -> Unit) {
        Log.i(TAG, "disabling virtual stick")
        VirtualStickManager.getInstance().disableVirtualStick(object : CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                onResult(true, null)
            }

            override fun onFailure(error: IDJIError) {
                onResult(false, error)
            }
        })
    }

    /**
     * forward/right/up/yaw are normalized [-1.0, 1.0], matching
     * app/drone/controller.py's MovementCommand exactly; this is the one
     * place that converts those fractions into this platform's real units.
     */
    fun sendVelocity(forward: Double, right: Double, up: Double, yaw: Double) {
        val param = VirtualStickFlightControlParam().apply {
            rollPitchCoordinateSystem = FlightCoordinateSystem.BODY
            rollPitchControlMode = RollPitchControlMode.VELOCITY
            verticalControlMode = VerticalControlMode.VELOCITY
            yawControlMode = YawControlMode.ANGULAR_VELOCITY

            pitch = clamp(forward * MAX_HORIZONTAL_SPEED_MPS, ROLL_PITCH_VELOCITY_CEILING)
            roll = clamp(right * MAX_HORIZONTAL_SPEED_MPS, ROLL_PITCH_VELOCITY_CEILING)
            verticalThrottle = clamp(up * MAX_VERTICAL_SPEED_MPS, VERTICAL_VELOCITY_CEILING)
            this.yaw = clamp(yaw * MAX_YAW_RATE_DEG_S, YAW_ANGULAR_VELOCITY_CEILING)
        }
        VirtualStickManager.getInstance().sendVirtualStickAdvancedParam(param)
    }

    fun sendHover() {
        sendVelocity(0.0, 0.0, 0.0, 0.0)
    }
}
