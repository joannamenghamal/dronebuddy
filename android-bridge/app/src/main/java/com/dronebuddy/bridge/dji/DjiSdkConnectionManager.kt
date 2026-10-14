package com.dronebuddy.bridge.dji

import android.content.Context
import android.util.Log
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.SDKManagerCallback

/**
 * Wraps SDKManager registration. init()/registerApp() and the full
 * SDKManagerCallback interface are confirmed via javap against the real
 * dji.v5.manager.SDKManager / dji.v5.manager.interfaces.SDKManagerCallback
 * classes in dji-sdk-v5-aircraft-provided:5.18.0 — not guessed.
 *
 * registerApp() is only called once Helper.install() has already run (in
 * DroneBuddyApplication.attachBaseContext) and MSDK has finished its own
 * internal init, signaled by onInitProcess(INITIALIZE_COMPLETE, ...) — not
 * called directly from registerAndInit(), since SDKManager.init() itself
 * drives that process asynchronously.
 */
class DjiSdkConnectionManager(private val appContext: Context) {

    companion object {
        private const val TAG = "DjiSdkConnection"
    }

    fun interface StatusListener {
        fun onStatusChanged(status: String)
    }

    fun interface AircraftConnectionListener {
        fun onAircraftConnectionChanged(connected: Boolean)
    }

    var statusListener: StatusListener? = null
    var aircraftConnectionListener: AircraftConnectionListener? = null

    private fun report(status: String) {
        Log.i(TAG, status)
        statusListener?.onStatusChanged(status)
    }

    /** Must be called after DroneBuddyApplication's Helper.install() has run. */
    fun registerAndInit() {
        report("registering")
        SDKManager.getInstance().init(appContext, object : SDKManagerCallback {
            override fun onRegisterSuccess() {
                report("register_success")
            }

            override fun onRegisterFailure(error: IDJIError) {
                report("register_failure: $error")
            }

            override fun onProductDisconnect(productId: Int) {
                report("product_disconnect: $productId")
                aircraftConnectionListener?.onAircraftConnectionChanged(false)
            }

            override fun onProductConnect(productId: Int) {
                report("product_connect: $productId")
                aircraftConnectionListener?.onAircraftConnectionChanged(true)
            }

            override fun onProductChanged(productId: Int) {
                report("product_changed: $productId")
            }

            override fun onInitProcess(event: DJISDKInitEvent, totalProcess: Int) {
                report("init_process: $event ($totalProcess%)")
                if (event == DJISDKInitEvent.INITIALIZE_COMPLETE) {
                    SDKManager.getInstance().registerApp()
                }
            }

            override fun onDatabaseDownloadProgress(current: Long, total: Long) {
                report("database_download_progress: $current/$total")
            }
        })
    }
}
