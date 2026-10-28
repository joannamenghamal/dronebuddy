package com.dronebuddy.bridge.dji

import android.util.Log
import com.dronebuddy.bridge.bridge.BridgeServer
import com.dronebuddy.bridge.protocol.BridgeMessage
import java.util.Timer
import java.util.TimerTask

/**
 * The app's side of the bridge: turns the commands BridgeServer carries in
 * from Python into DJI SDK calls. BridgeServer itself never touches the SDK.
 *
 * Safety-critical behaviors implemented here per DRONE_BRIDGE.md /
 * SAFETY.md, independent of whatever the Python-side SafetyManager also
 * does - the app must not trust the far end to always behave:
 *  - staleCommandTimeoutMs: while a client is connected, if no valid
 *    flight_command arrives in time, force a hover rather than continuing
 *    the last velocity indefinitely. This also covers a silent link, since
 *    a silent link delivers no commands.
 *  - Client connect, disconnect and link loss all force a hover - never
 *    the last command received.
 *
 * takeoff/land go through DjiFlightActions (plain DJIKey action calls), not
 * the virtual stick - those two are the one pair of commands that must work
 * even before virtual stick is enabled.
 */
class DjiCommandHandler(
    private val virtualStick: DjiVirtualStickController,
    private val staleCommandTimeoutMs: Long = 1000L,
) : BridgeServer.Handler {

    companion object {
        private const val TAG = "DjiCommandHandler"
        private const val CHECK_INTERVAL_MS = 200L
    }

    @Volatile private var clientConnected = false
    @Volatile private var lastFlightCommandAtMs: Long = 0L
    private val watchdogTimer = Timer("dji-command-watchdog", true)

    fun start() {
        watchdogTimer.scheduleAtFixedRate(
            object : TimerTask() {
                override fun run() {
                    if (!clientConnected) return
                    if (System.currentTimeMillis() - lastFlightCommandAtMs >= staleCommandTimeoutMs) {
                        virtualStick.sendHover()
                    }
                }
            },
            CHECK_INTERVAL_MS,
            CHECK_INTERVAL_MS,
        )
    }

    fun stop() {
        watchdogTimer.cancel()
    }

    override fun onClientConnected() {
        clientConnected = true
        lastFlightCommandAtMs = System.currentTimeMillis()
        virtualStick.sendHover()
    }

    override fun onClientDisconnected() {
        clientConnected = false
        virtualStick.sendHover()
    }

    override fun onLinkLost() {
        Log.w(TAG, "bridge link lost, hovering")
        virtualStick.sendHover()
    }

    override fun onFlightCommand(command: BridgeMessage.FlightCommand) {
        lastFlightCommandAtMs = System.currentTimeMillis()
        virtualStick.sendVelocity(command.forward, command.right, command.up, command.yaw)
    }

    override fun onEmergencyStop() {
        virtualStick.sendHover()
    }

    override fun onTakeoff(reply: (ok: Boolean, detail: String?) -> Unit) {
        DjiFlightActions.takeoff { ok, error -> reply(ok, error?.toString()) }
    }

    override fun onLand(reply: (ok: Boolean, detail: String?) -> Unit) {
        DjiFlightActions.land { ok, error -> reply(ok, error?.toString()) }
    }
}
