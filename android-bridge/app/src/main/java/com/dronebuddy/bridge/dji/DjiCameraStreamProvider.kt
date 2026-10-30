package com.dronebuddy.bridge.dji

import android.graphics.Bitmap
import dji.sdk.keyvalue.value.common.ComponentIndexType
import dji.v5.manager.datacenter.camera.CameraStreamManager
import dji.v5.manager.interfaces.ICameraStreamManager
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer

/**
 * MSDK V5 delivers decoded camera frames through CameraStreamManager's
 * frame-listener API. Confirmed via javap against
 * dji-sdk-v5-aircraft-provided:5.18.0 — not guessed:
 *  - CameraStreamManager.getInstance(): CameraStreamManager
 *  - addFrameListener(ComponentIndexType, FrameFormat, CameraFrameListener)
 *  - CameraFrameListener.onFrame(ByteArray, offset: Int, length: Int, width: Int, height: Int, FrameFormat)
 * FrameFormat.RGBA_8888's in-memory byte layout (R,G,B,A per pixel) matches
 * Android's Bitmap.Config.ARGB_8888 exactly, so the raw buffer can be copied
 * straight into a Bitmap with no manual YUV conversion.
 *
 * LEFT_OR_MAIN is the ComponentIndexType DJI's own MSDK V5 samples bind for
 * aircraft with a single gimbal camera (the Mini 3 has no separate FPV
 * camera) — UNVERIFIED against a physical Mini 3, since this environment
 * has no hardware to confirm which index the aircraft actually reports.
 *
 * This app never shows the feed on screen, so it has no Surface for MSDK to
 * render into. Without one, MSDK doesn't decode the stream at all and frame
 * listeners never fire - setKeepAliveDecoding(true) keeps the decoder
 * running anyway (CameraStreamManager only attaches a stream source when a
 * render target exists or keep-alive decoding is on).
 *
 * Start this once the aircraft is connected, not at app launch: before
 * then the SDK may not have finished initializing.
 *
 * Throttled to minIntervalMs between processed frames: the raw feed can push
 * far faster than the follow-me loop (app/main.py) consumes frames, or than
 * the WebSocket link to the Python side can carry comfortably — the
 * person-tracking loop gains nothing from frames it never asks for between
 * get_video_frame() calls.
 */
class DjiCameraStreamProvider {

    @Volatile private var listener: ICameraStreamManager.CameraFrameListener? = null

    fun startListening(minIntervalMs: Long = 100L, jpegQuality: Int = 70, onFrame: (ByteArray) -> Unit) {
        stopListening()
        var lastProcessedAtMs = 0L
        val frameListener = ICameraStreamManager.CameraFrameListener { data, offset, length, width, height, format ->
            val now = System.currentTimeMillis()
            if (format != ICameraStreamManager.FrameFormat.RGBA_8888 || now - lastProcessedAtMs < minIntervalMs) {
                return@CameraFrameListener
            }
            lastProcessedAtMs = now

            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            bitmap.copyPixelsFromBuffer(ByteBuffer.wrap(data, offset, length))
            val out = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, jpegQuality, out)
            bitmap.recycle()
            onFrame(out.toByteArray())
        }

        listener = frameListener
        CameraStreamManager.getInstance().setKeepAliveDecoding(true)
        CameraStreamManager.getInstance().addFrameListener(
            ComponentIndexType.LEFT_OR_MAIN,
            ICameraStreamManager.FrameFormat.RGBA_8888,
            frameListener,
        )
    }

    fun stopListening() {
        val current = listener ?: return
        listener = null
        CameraStreamManager.getInstance().removeFrameListener(current)
        CameraStreamManager.getInstance().setKeepAliveDecoding(false)
    }
}
