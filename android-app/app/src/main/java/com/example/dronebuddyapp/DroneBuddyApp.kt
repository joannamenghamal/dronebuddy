package com.example.dronebuddyapp

import android.app.Application
import android.content.Context
import android.util.Log

// Apparently, DJI needs this to import the SDK decryption and protection package
class DroneBuddyApp : Application() {
    override fun attachBaseContext(base: Context?) {
        super.attachBaseContext(base)
        com.cySdkyc.clx.Helper.install(this)
        Log.d("App Init", "Helper has initialized")
    }
}