package com.example.dronebuddyapp.dronecontrollers

import android.util.Log
import com.example.dronebuddyapp.bridge.BridgeServer
import com.example.dronebuddyapp.bridge.BridgeMessage
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
 *  - Except during a takeoff or landing: Python deliberately stops sending
 *    flight_commands then (app/main.py sends nothing after asking to land),
 *    and a stream of hover inputs could cancel DJI's auto-landing or stall
 *    the takeoff climb. The aircraft holds position by itself without
 *    stick input, so nothing is lost. The next flight_command, or an
 *    emergency_stop, ends this.
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
    @Volatile private var autoFlightActionInProgress = false
    private val watchdogTimer = Timer("dji-command-watchdog", true)

    fun start() {
        watchdogTimer.scheduleAtFixedRate(
            object : TimerTask() {
                override fun run() {
                    if (!clientConnected || autoFlightActionInProgress) return
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
        if (!autoFlightActionInProgress) virtualStick.sendHover()
    }

    override fun onLinkLost() {
        if (autoFlightActionInProgress) {
            Log.w(TAG, "bridge link lost during takeoff/landing, letting it finish")
            return
        }
        Log.w(TAG, "bridge link lost, hovering")
        virtualStick.sendHover()
    }

    override fun onFlightCommand(command: BridgeMessage.FlightCommand) {
        autoFlightActionInProgress = false
        lastFlightCommandAtMs = System.currentTimeMillis()
        virtualStick.sendVelocity(command.forward, command.right, command.up, command.yaw)
    }

    override fun onEmergencyStop() {
        autoFlightActionInProgress = false
        virtualStick.sendHover()
    }

    override fun onTakeoff(reply: (ok: Boolean, detail: String?) -> Unit) {
        autoFlightActionInProgress = true
        DjiFlightActions.takeoff { ok, error ->
            if (!ok) autoFlightActionInProgress = false
            reply(ok, error?.toString())
        }
    }

    override fun onLand(reply: (ok: Boolean, detail: String?) -> Unit) {
        autoFlightActionInProgress = true
        DjiFlightActions.land { ok, error ->
            if (!ok) autoFlightActionInProgress = false
            reply(ok, error?.toString())
        }
    }
}
