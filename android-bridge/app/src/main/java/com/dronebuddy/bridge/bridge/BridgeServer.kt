package com.dronebuddy.bridge.bridge

import android.util.Log
import com.dronebuddy.bridge.protocol.BridgeMessage
import com.dronebuddy.bridge.protocol.ProtocolCodec
import org.java_websocket.WebSocket
import org.java_websocket.exceptions.WebsocketNotConnectedException
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
 * This class only carries messages. It never touches the DJI SDK: the app
 * (MainActivity and the dji/ classes) owns the aircraft connection and
 * decides what every command means for the aircraft. Inbound messages are
 * decoded and handed to [Handler]; outbound telemetry/video/acks are sent on
 * the app's behalf.
 *
 * The one thing it does on its own is notice link silence: if no message
 * (including heartbeats) arrives within connectionLossTimeoutMs, it tells
 * the handler via [Handler.onLinkLost] - onMessage alone would never fire
 * again to notice a client that simply stopped sending. Every inbound
 * flight_command is validated by ProtocolCodec before it is handed on, so
 * malformed input never reaches the app.
 */
class BridgeServer(
    port: Int,
    private val handler: Handler,
    private val connectionLossTimeoutMs: Long = 3000L,
) : WebSocketServer(InetSocketAddress(port)) {

    /**
     * Implemented by the app side that owns the aircraft. Called on the
     * WebSocket server's threads; implementations must not block.
     */
    interface Handler {
        fun onClientConnected()

        /** Socket closed or errored. */
        fun onClientDisconnected()

        /** Socket still open but silent for connectionLossTimeoutMs. Fires once per silence. */
        fun onLinkLost()

        /** Already validated by ProtocolCodec. */
        fun onFlightCommand(command: BridgeMessage.FlightCommand)

        fun onEmergencyStop()

        /** Call [reply] once the action has succeeded or failed; it sends the ack. */
        fun onTakeoff(reply: (ok: Boolean, detail: String?) -> Unit)

        fun onLand(reply: (ok: Boolean, detail: String?) -> Unit)
    }

    companion object {
        private const val TAG = "BridgeServer"
    }

    @Volatile private var lastMessageAtMs: Long = 0L
    @Volatile private var linkLostReported = false
    @Volatile private var activeClient: WebSocket? = null
    private val watchdogTimer = Timer("bridge-watchdog", true)

    override fun onOpen(conn: WebSocket, handshake: ClientHandshake) {
        Log.i(TAG, "client connected: ${conn.remoteSocketAddress}")
        activeClient = conn
        lastMessageAtMs = System.currentTimeMillis()
        linkLostReported = false
        handler.onClientConnected()
    }

    override fun onClose(conn: WebSocket, code: Int, reason: String, remote: Boolean) {
        Log.w(TAG, "client disconnected: code=$code reason=$reason")
        if (activeClient === conn) {
            activeClient = null
            handler.onClientDisconnected()
        }
    }

    override fun onMessage(conn: WebSocket, message: String) {
        lastMessageAtMs = System.currentTimeMillis()
        linkLostReported = false
        val json = try {
            JSONObject(message)
        } catch (e: Exception) {
            Log.w(TAG, "malformed JSON, ignoring: ${e.message}")
            return
        }

        when (ProtocolCodec.messageType(json)) {
            "flight_command" -> handleFlightCommand(conn, json)
            "heartbeat" -> sendQuietly(conn, ProtocolCodec.encodeAck(BridgeMessage.Ack("heartbeat", true)))
            "emergency_stop" -> {
                Log.w(TAG, "emergency_stop received from client")
                handler.onEmergencyStop()
                sendQuietly(conn, ProtocolCodec.encodeAck(BridgeMessage.Ack("emergency_stop", true)))
            }
            "takeoff" -> handler.onTakeoff { ok, detail ->
                sendQuietly(conn, ProtocolCodec.encodeAck(BridgeMessage.Ack("takeoff", ok, detail)))
            }
            "land" -> handler.onLand { ok, detail ->
                sendQuietly(conn, ProtocolCodec.encodeAck(BridgeMessage.Ack("land", ok, detail)))
            }
            else -> Log.w(TAG, "unknown message type, ignoring")
        }
    }

    private fun handleFlightCommand(conn: WebSocket, json: JSONObject) {
        val cmd = ProtocolCodec.decodeFlightCommand(json)
        if (cmd == null) {
            sendQuietly(
                conn,
                ProtocolCodec.encodeAck(
                    BridgeMessage.Ack("flight_command", false, "validation failed")
                ),
            )
            return
        }
        handler.onFlightCommand(cmd)
        sendQuietly(conn, ProtocolCodec.encodeAck(BridgeMessage.Ack("flight_command", true)))
    }

    override fun onError(conn: WebSocket?, ex: Exception) {
        Log.e(TAG, "socket error", ex)
        if (conn != null && conn === activeClient) {
            handler.onClientDisconnected()
        }
    }

    override fun onStart() {
        Log.i(TAG, "listening on port $port")
        startWatchdog()
    }

    private fun startWatchdog() {
        val checkIntervalMs = 200L
        watchdogTimer.scheduleAtFixedRate(
            object : TimerTask() {
                override fun run() {
                    activeClient ?: return
                    val silentForMs = System.currentTimeMillis() - lastMessageAtMs
                    if (silentForMs >= connectionLossTimeoutMs && !linkLostReported) {
                        Log.w(TAG, "connection loss: no message for ${silentForMs}ms")
                        linkLostReported = true
                        handler.onLinkLost()
                    }
                }
            },
            checkIntervalMs,
            checkIntervalMs,
        )
    }

    /**
     * The client can disconnect between any check and the send - e.g. a
     * takeoff/land reply arriving from a DJI callback after Python went
     * away - and java-websocket throws in that case. Dropping the message
     * is right: there's no one left to receive it.
     */
    private fun sendQuietly(conn: WebSocket?, message: String) {
        try {
            conn?.send(message)
        } catch (e: WebsocketNotConnectedException) {
            Log.d(TAG, "client gone, dropping outbound message")
        }
    }

    fun sendTelemetry(telemetry: BridgeMessage.Telemetry) {
        sendQuietly(activeClient, ProtocolCodec.encodeTelemetry(telemetry))
    }

    /**
     * Video frames go out as raw binary WS frames (JPEG bytes, no JSON
     * envelope) rather than through ProtocolCodec — DRONE_BRIDGE.md leaves
     * them a separate channel on the same socket from the JSON control/
     * telemetry traffic, since base64-wrapping a binary blob into JSON would
     * cost ~33% more bandwidth for no benefit on a link this latency-sensitive.
     */
    fun sendVideoFrame(jpegBytes: ByteArray) {
        try {
            activeClient?.send(jpegBytes)
        } catch (e: WebsocketNotConnectedException) {
            Log.d(TAG, "client gone, dropping video frame")
        }
    }

    fun shutdownServer() {
        watchdogTimer.cancel()
        thread { stop() }
    }
}
