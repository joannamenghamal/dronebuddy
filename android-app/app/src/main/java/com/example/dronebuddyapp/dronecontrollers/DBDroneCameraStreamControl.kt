package com.example.dronebuddyapp.dronecontrollers

import android.view.Surface
import android.view.SurfaceHolder
import android.view.SurfaceView
import com.example.dronebuddyapp.logcontent.LogItem
import dji.sdk.keyvalue.value.common.ComponentIndexType
import dji.v5.manager.datacenter.camera.CameraStreamManager
import dji.v5.manager.interfaces.ICameraStreamManager
import kotlinx.coroutines.flow.MutableStateFlow

class DBDroneCameraStreamControl {
    private val cameraStreamManager : ICameraStreamManager = CameraStreamManager.getInstance()
    private val cameraListener = object : ICameraStreamManager.AvailableCameraUpdatedListener {
        override fun onAvailableCameraUpdated(availableCameraList: List<ComponentIndexType>) {
            availableCameras = availableCameraList
        }

        override fun onCameraStreamEnableUpdate(cameraStreamEnableMap: Map<ComponentIndexType, Boolean?>) {

        //    super.onCameraStreamEnableUpdate(cameraStreamEnableMap)
        }
    }
    private var availableCameras = emptyList<ComponentIndexType>()
    private var surfaceExists = false
    private val cameraZoomScale = ICameraStreamManager.ScaleType.CENTER_INSIDE

    fun setupCamera() {
        // Request for cameras indexes, to put into the cameralistener
        cameraStreamManager.addAvailableCameraUpdatedListener(cameraListener)
    }

    fun destroyCamera() {
        cameraStreamManager.removeAvailableCameraUpdatedListener(cameraListener)
    }

    fun addSurfaceDisplay(cameraIndex : Int, surfaceView: SurfaceView) {
        // Create a surface holder reference to get height and width
        val surfaceHolder = surfaceView.holder.addCallback(object: SurfaceHolder.Callback {
            override fun surfaceChanged(p0: SurfaceHolder, p1: Int, p2: Int, p3: Int) {
                // p2 is width, p3 is height
                LogItem.addLog("CameraView", "Camera Surface Changed", LogItem.Status.WARNING)
                if (availableCameras.isEmpty()) {
                    LogItem.addLog("CameraView", "No Cameras Found!", LogItem.Status.ERROR)
                }
                else {
                    cameraStreamManager.putCameraStreamSurface(
                        availableCameras.get(0), // our dji mini 3 only has one camera
                        surfaceView.holder.surface,
                        p2,
                        p3,
                        cameraZoomScale
                    )
                }


            }

            override fun surfaceCreated(p0: SurfaceHolder) {
                // Nothing
                surfaceExists = true
                LogItem.addLog("CameraView", "Created Camera Surface", LogItem.Status.INFO)
            }

            override fun surfaceDestroyed(p0: SurfaceHolder) {
                LogItem.addLog("CameraView", "Destroyed Camera Surface", LogItem.Status.WARNING)
                cameraStreamManager.removeCameraStreamSurface(surfaceView.holder.surface)
                surfaceExists = false
            }
        })

    }
}