package com.dronebuddy.bridge.bridge

import android.util.Log
import com.dronebuddy.bridge.dji.DjiFlightActions
import com.dronebuddy.bridge.dji.DjiVirtualStickController
import com.dronebuddy.bridge.protocol.BridgeMessage
import com.dronebuddy.bridge.protocol.ProtocolCodec
import org.java_websocket.WebSocket
import org.java_websocket.handshake.ClientHandshake
import org.java_websocket.server.WebSocketServer
import org.json.JSONObject
import java.net.InetSocketAddress
import java.util.Timer
import java.util.TimerTask
import kotlin.concurrent.thread

/**
 * Server-side half of DRONE_BRIDGE.md's protocol. The Python autonomy
 * process is the client; this app is the server, since the aircraft-side
 * connection (this phone/RC) is the one with a stable, known address on the
 * local network while the Python process may be run from any machine that
 * can reach it.
 *
 * Safety-critical behaviors implemented here per DRONE_BRIDGE.md /
 * SAFETY.md, independent of whatever the Python-side SafetyManager also
 * does - this app must not trust the far end to always behave:
 *  - staleCommandTimeoutMs: if no valid flight_command arrives in time,
 *    force a hover rather than continuing the last velocity indefinitely.
 *  - connectionLossTimeoutMs: if the socket itself doesn't produce any
 *    message (including heartbeats) in time, force a hover/land.
 *  - Every inbound flight_command is validated by ProtocolCodec before it
 *    reaches DjiVirtualStickController; malformed input never reaches
 *    virtual stick.
 *
 * takeoff/land go through DjiFlightActions (plain DJIKey action calls), not
 * the virtual stick - those two are the one pair of commands that must work
 * even before virtual stick is enabled.
 */
class BridgeServer(
    port: Int,
    private val virtualStick: DjiVirtualStickController,
    private val staleCommandTimeoutMs: Long = 1000L,
    private val connectionLossTimeoutMs: Long = 3000L,
) : WebSocketServer(InetSocketAddress(port)) {

    companion object {
        private const val TAG = "BridgeServer"
    }

    @Volatile private var lastMessageAtMs: Long = 0L
    @Volatile private var activeClient: WebSocket? = null
    private val watchdogTimer = Timer("bridge-watchdog", true)

    override fun onOpen(conn: WebSocket, handshake: ClientHandshake) {
        Log.i(TAG, "client connected: ${conn.remoteSocketAddress}")
        activeClient = conn
        lastMessageAtMs = System.currentTimeMillis()
        virtualStick.sendHover()
    }

    override fun onClose(conn: WebSocket, code: Int, reason: String, remote: Boolean) {
        Log.w(TAG, "client disconnected: code=$code reason=$reason")
        if (activeClient === conn) {
            activeClient = null
            virtualStick.sendHover()
        }
    }

    override fun onMessage(conn: WebSocket, message: String) {
        lastMessageAtMs = System.currentTimeMillis()
        val json = try {
            JSONObject(message)
        } catch (e: Exception) {
            Log.w(TAG, "malformed JSON, ignoring: ${e.message}")
            return
        }

        when (ProtocolCodec.messageType(json)) {
            "flight_command" -> handleFlightCommand(conn, json)
            "heartbeat" -> conn.send(ProtocolCodec.encodeAck(BridgeMessage.Ack("heartbeat", true)))
            "emergency_stop" -> {
                Log.w(TAG, "emergency_stop received from client")
                virtualStick.sendHover()
                conn.send(ProtocolCodec.encodeAck(BridgeMessage.Ack("emergency_stop", true)))
            }
            "takeoff" -> DjiFlightActions.takeoff { ok, error ->
                conn.send(ProtocolCodec.encodeAck(BridgeMessage.Ack("takeoff", ok, error?.toString())))
            }
            "land" -> DjiFlightActions.land { ok, error ->
                conn.send(ProtocolCodec.encodeAck(BridgeMessage.Ack("land", ok, error?.toString())))
            }
            else -> Log.w(TAG, "unknown message type, ignoring")
        }
    }

    private fun handleFlightCommand(conn: WebSocket, json: JSONObject) {
        val cmd = ProtocolCodec.decodeFlightCommand(json)
        if (cmd == null) {
            conn.send(
                ProtocolCodec.encodeAck(
                    BridgeMessage.Ack("flight_command", false, "validation failed")
                )
            )
            return
        }
        virtualStick.sendVelocity(cmd.forward, cmd.right, cmd.up, cmd.yaw)
        conn.send(ProtocolCodec.encodeAck(BridgeMessage.Ack("flight_command", true)))
    }

    override fun onError(conn: WebSocket?, ex: Exception) {
        Log.e(TAG, "socket error", ex)
        virtualStick.sendHover()
    }

    override fun onStart() {
        Log.i(TAG, "listening on port $port")
        startWatchdog()
    }

    /**
     * Runs independently of onMessage so a client that simply stops sending
     * (crash, network partition) still gets caught - onMessage alone would
     * never fire again to notice the silence.
     */
    private fun startWatchdog() {
        val checkIntervalMs = 200L
        watchdogTimer.scheduleAtFixedRate(
            object : TimerTask() {
                override fun run() {
                    val client = activeClient ?: return
                    val silentForMs = System.currentTimeMillis() - lastMessageAtMs
                    when {
                        silentForMs >= connectionLossTimeoutMs -> {
                            Log.w(TAG, "connection loss: no message for ${silentForMs}ms")
                            virtualStick.sendHover()
                        }
                        silentForMs >= staleCommandTimeoutMs -> {
                            virtualStick.sendHover()
                        }
                    }
                }
            },
            checkIntervalMs,
            checkIntervalMs,
        )
    }

    fun broadcastTelemetry(telemetry: BridgeMessage.Telemetry) {
        activeClient?.send(ProtocolCodec.encodeTelemetry(telemetry))
    }

    fun shutdownServer() {
        watchdogTimer.cancel()
        thread { stop() }
    }
}
