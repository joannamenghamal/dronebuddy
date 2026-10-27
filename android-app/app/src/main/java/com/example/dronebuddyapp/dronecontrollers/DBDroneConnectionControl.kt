package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.ISDKManager
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.manager.interfaces.SDKManagerCallback
import android.util.Log
import com.example.dronebuddyapp.logcontent.LogItem

class DBDroneConnectionControl(private val context: Context) {
    private val sdkManager = SDKManager.getInstance()
    private val sdkManagerCallback = object: SDKManagerCallback {
        override fun onInitProcess(event: DJISDKInitEvent?, totalProcess: Int) {

            if (event == DJISDKInitEvent.INITIALIZE_COMPLETE) {
                // Log.d("DJI Connection", "DJI initialization complete")
                LogItem.addLog("DJI Connection", "DJI Initialization Complete")
                sdkManager.registerApp()
            }

        }

        override fun onRegisterSuccess() {
            // Log.d("DJI Connection", "Register Success!")
            LogItem.addLog("DJI Connection", "Register Success")
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