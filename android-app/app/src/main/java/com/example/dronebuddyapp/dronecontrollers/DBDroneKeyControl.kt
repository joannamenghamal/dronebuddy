package com.example.dronebuddyapp.dronecontrollers

import com.example.dronebuddyapp.logcontent.LogItem
import dji.sdk.keyvalue.key.DJIActionKeyInfo
import dji.sdk.keyvalue.key.DJIKey
import dji.sdk.keyvalue.key.DJIKeyInfo
import dji.sdk.keyvalue.key.KeyTools
import dji.sdk.keyvalue.value.common.LocationCoordinate3D
import dji.sdk.keyvalue.value.common.Velocity3D
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.KeyManager
import dji.v5.manager.interfaces.IKeyManager

// The keys are necessary to control and view hardware details / settings
// The most important key application will be the access to flight stats, like speed, height, etc.
class DBDroneKeyControl {
    private val keyManager : IKeyManager = KeyManager.getInstance()
    // val sampleKey = keyManager.getValue(KeyTools.createKey(FlightControllerKey.KeyAltitude))

    // Create Key ListenerskeyManager.getValue(KeyTools.createKey(FlightControllerKey.KeyAircraftLocation3D))
    // This function spawns a keylistener, attaches it to this DBDroneKeyControl Class
    // Needs the desired DJIKeyInfo and Callback so that people can attach custom behavior to the callback
    // Example of DJIKeyInfo is FlightControllerKey.KeyConnection
    // Return a DJIKey<T>
    fun <T> spawnKeyListeners(keyInfo : DJIKeyInfo<T>, callback: CommonCallbacks.KeyListener<T>) : DJIKey<T> {
        val djikey = KeyTools.createKey(keyInfo) // createKey returns a DJIKey, which is needed to disconnect specific keys
        keyManager.listen(
            djikey,
            this,
            callback // Test
        )

        return djikey
    }

    fun <T> disconnectKeyListener(key : DJIKey<T>) {
        keyManager.cancelListen(key, this)
    }

    fun disconnectAllKeyListeners() {
        keyManager.cancelListen(this)
    }

    // Example of DJIKeyInfo is FlightControllerKey.KeyConnection
    // Returns a nullable, so you need to deal with the fact it can be null
    fun <T> getKeyValueOnce(keyInfo : DJIKeyInfo<T>) : T? {
        val djikey = KeyTools.createKey(keyInfo)
        return keyManager.getValue<T>(djikey)
    }

    fun <T> setKeyValueOnce(keyInfo : DJIKeyInfo<T>, data: T) : CommonCallbacks.CompletionCallback {
        val djikey = KeyTools.createKey(keyInfo)
        val callback = object: CommonCallbacks.CompletionCallback {
            override fun onSuccess() {
                LogItem.addLog("Key Control", "Single Key Set Success, Is Now: $data", LogItem.Status.INFO)
            }

            override fun onFailure(p0: IDJIError) {
                LogItem.addLog("Key Control", "Single Key Set Error: $p0", LogItem.Status.ERROR)
            }
        }
        keyManager.setValue(djikey, data, callback)

        return callback
    }

    fun <T, R> performActionOnce(
        keyInfo : DJIActionKeyInfo<T, R>,
        logAction : String,
        successLambda: ((R?) -> Unit)? = null,
        failLambda: ((IDJIError) -> Unit)? = null
    ) {
        val djikey = KeyTools.createKey(keyInfo)
        val callback = object: CommonCallbacks.CompletionCallbackWithParam<R> {
            override fun onSuccess(p0: R?) {
                LogItem.addLog("Key Control", "$logAction - Single Action Performed Complete: $p0", LogItem.Status.INFO)
                successLambda?.invoke(p0)
            }
            override fun onFailure(p0: IDJIError) {
                LogItem.addLog("Key Control", "$logAction - Single Action Performed Failed! Status: $p0", LogItem.Status.ERROR)
                failLambda?.invoke(p0)
            }
        }
        keyManager.performAction(djikey, callback)
    }


}

// Below are some examples of callbacks
var aircraftConnectionStatus = object: CommonCallbacks.KeyListener<Boolean> {
    override fun onValueChange(p0: Boolean?, p1: Boolean?) {
        TODO("Not yet implemented")
    }
}

// keyManager.getValue(KeyTools.createKey(FlightControllerKey.KeyAircraftLocation3D))
var aircraftLocation3D = object: CommonCallbacks.KeyListener<LocationCoordinate3D> {
    override fun onValueChange(p0: LocationCoordinate3D?, p1: LocationCoordinate3D?) {
        TODO("Not yet implemented")
    }
}

// keyManager.getValue(KeyTools.createKey(FlightControllerKey.KeyAircraftVelocity))
var aircraftVelocity = object: CommonCallbacks.KeyListener<Velocity3D> {
    override fun onValueChange(p0: Velocity3D?, p1: Velocity3D?) {
        TODO("Not yet implemented")
    }
}