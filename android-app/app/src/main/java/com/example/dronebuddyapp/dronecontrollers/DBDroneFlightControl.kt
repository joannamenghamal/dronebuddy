package dji.sampleV5.aircraft.visualbuddy

import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.aircraft.virtualstick.IStick
import dji.v5.manager.interfaces.IVirtualStickManager
import dji.v5.manager.aircraft.virtualstick.VirtualStickManager

// Class will create all important aspects we need for virtual drone control
// Use the VirtualStickManager for virtual sticks
// Convention is NED (North - East - Down)
// Essentially have to use the virtualstickmanager and get the instance.
class DBDroneFlightControl() {
    private val stickManager : IVirtualStickManager = VirtualStickManager.getInstance()
    val leftStick = DBStickCreate(stickManager, true)
    val rightStick = DBStickCreate(stickManager, false)
    var enableVirtualMode: Boolean = false
        // Kotlin custom setter
        set(bool) {
            val fail = setVirtualStickMode(bool)
            if (!fail) {
                enableVirtualMode = bool
            }
        }

    // Returns true if it failed to do action
    fun setVirtualStickMode(bool: Boolean) : Boolean {
        var failed = false
        if (bool) {
            stickManager.enableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    // ToastUtils.showToast("enableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    // ToastUtils.showToast("enableVirtualStick error,$error")
                    failed = true
                }
            })
        }
        else {
            stickManager.disableVirtualStick(object : CommonCallbacks.CompletionCallback {
                override fun onSuccess() {
                    // ToastUtils.showToast("disableVirtualStick success.")
                }

                override fun onFailure(error: IDJIError) {
                    // ToastUtils.showToast("disableVirtualStick error,$error")
                    failed = true
                }
            })

        }
        return failed
    }

}

// Used for handling the stick creating instance
class DBStickCreate(val stickManager: IVirtualStickManager, val leftOnTrue: Boolean) {
    val virtualStick: IStick
    init {
        if (leftOnTrue) {
            virtualStick = stickManager.leftStick
        } else {
            virtualStick = stickManager.rightStick
        }
    }

    var strength_v: Int = 0
        set(newVal) {
            val clamped = newVal.coerceIn(-660, 600)

            virtualStick.verticalPosition = clamped
        }
    var strength_h: Int = 0
        set(newVal) {
            val clamped = newVal.coerceIn(-660, 600)

            virtualStick.horizontalPosition = clamped
        }




}
