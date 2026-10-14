package com.dronebuddy.bridge

import android.app.Application
import android.content.Context
import com.cySdkyc.clx.Helper

/**
 * DJI's MSDK V5 decrypts/patches its own classes at runtime via a Helper
 * installed from Application.attachBaseContext(), before any other SDK
 * class is touched. com.cySdkyc.clx.Helper.install(Application) is
 * confirmed (via javap) against the real classes.jar inside
 * dji-sdk-v5-aircraft:5.18.0 — com.secneo.sdk, referenced in some MSDK
 * V4-era guides, has no Helper class in that artifact.
 */
class DroneBuddyApplication : Application() {

    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(base)
        Helper.install(this)
    }
}
