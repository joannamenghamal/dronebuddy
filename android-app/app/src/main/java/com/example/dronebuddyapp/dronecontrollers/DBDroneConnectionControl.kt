package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.ISDKManager
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.manager.interfaces.SDKManagerCallback

class DBDroneConnectionControl(private val context: Context) {
    private val sdkManager = SDKManager.getInstance()
    private val sdkManagerCallback = object: SDKManagerCallback {
        override fun onInitProcess(event: DJISDKInitEvent?, totalProcess: Int) {

            if (event == DJISDKInitEvent.INITIALIZE_COMPLETE) {
                sdkManager.registerApp()
            }

        }

        override fun onRegisterSuccess() {
            TODO("Not yet implemented")

        }

        override fun onRegisterFailure(error: IDJIError?) {
            TODO("Not yet implemented")
        }

        override fun onProductConnect(productId: Int) {
            TODO("Not yet implemented")
        }

        override fun onProductDisconnect(productId: Int) {
            TODO("Not yet implemented")
        }

        override fun onDatabaseDownloadProgress(current: Long, total: Long) {
            TODO("Not yet implemented")
        }

        override fun onProductChanged(productId: Int) {
            TODO("Not yet implemented")
        }
    }

    init {
        // Attempt to initialize, which will then try to register the app
        sdkManager.init(context, sdkManagerCallback)
    }
}