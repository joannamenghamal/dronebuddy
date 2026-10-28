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
                LogItem.addLog("DJI Connection", "DJI Initialization Complete", LogItem.Status.ERROR)
                sdkManager.registerApp()
            }

        }

        override fun onRegisterSuccess() {
            // Log.d("DJI Connection", "Register Success!")
            LogItem.addLog("DJI Connection", "Register Success", LogItem.Status.WARNING)
        }

        override fun onRegisterFailure(error: IDJIError?) {
            LogItem.addLog("DJI Connection", "Register Failed", LogItem.Status.ERROR)
        }

        override fun onProductConnect(productId: Int) {
            LogItem.addLog("DJI Connection", "Product Connected (Prod ID: ${productId}", LogItem.Status.INFO)
        }

        override fun onProductDisconnect(productId: Int) {
            LogItem.addLog("DJI Connection", "Product Disconnected (Prod ID: ${productId}", LogItem.Status.WARNING)
        }

        override fun onDatabaseDownloadProgress(current: Long, total: Long) {
            LogItem.addLog("DJI Connection", "Database Download Progress: ${current}/${total}", LogItem.Status.INFO)
        }

        override fun onProductChanged(productId: Int) {
            LogItem.addLog("DJI Connection", "Product Channged (Prod ID: ${productId}", LogItem.Status.INFO)
        }
    }

    init {
        // Attempt to initialize, which will then try to register the app
        sdkManager.init(context, sdkManagerCallback)
    }
}