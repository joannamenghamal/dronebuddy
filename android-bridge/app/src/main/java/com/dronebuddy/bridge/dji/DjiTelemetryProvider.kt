package com.dronebuddy.bridge.dji

import dji.sdk.keyvalue.key.BatteryKey
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.v5.et.create
import dji.v5.et.listen
import dji.v5.manager.KeyManager
import java.util.concurrent.atomic.AtomicReference

/**
 * MSDK V5 exposes telemetry through its generic KeyManager/DJIKey system.
 * Every key below (and the create()/listen()/cancelListen() call shapes)
 * was confirmed via javap against the real classes in
 * dji-sdk-v5-aircraft-provided:5.18.0 — not guessed:
 *  - FlightControllerKey.KeyConnection: DJIKeyInfo<Boolean>
 *  - FlightControllerKey.KeyAltitude: DJIKeyInfo<Double>
 *  - FlightControllerKey.KeyAircraftLocation: DJIKeyInfo<LocationCoordinate2D>
 *  - FlightControllerKey.KeyAircraftVelocity: DJIKeyInfo<Velocity3D>
 *  - FlightControllerKey.KeyCompassHeading: DJIKeyInfo<Double>
 *  - BatteryKey.KeyChargeRemainingInPercent: DJIKeyInfo<Integer>
 * KeyChargeRemainingInPercent.create() (no component index) targets the
 * aircraft's single/aggregate battery, which is correct for a Mini 3.
 */
class DjiTelemetryProvider {

    data class Snapshot(
        val battery: Int?,
        val latitude: Double?,
        val longitude: Double?,
        val altitude: Double?,
        val heading: Double?,
        val velocityX: Double?,
        val velocityY: Double?,
        val velocityZ: Double?,
    )

    private val latest = AtomicReference(
        Snapshot(null, null, null, null, null, null, null, null)
    )

    fun startListening(onUpdate: (Snapshot) -> Unit) {
        fun publish(update: (Snapshot) -> Snapshot) {
            onUpdate(latest.updateAndGet(update))
        }

        BatteryKey.KeyChargeRemainingInPercent.create().listen(this) { percent ->
            publish { it.copy(battery = percent) }
        }
        FlightControllerKey.KeyAircraftLocation.create().listen(this) { location ->
            publish { it.copy(latitude = location?.latitude, longitude = location?.longitude) }
        }
        FlightControllerKey.KeyAltitude.create().listen(this) { altitude ->
            publish { it.copy(altitude = altitude) }
        }
        FlightControllerKey.KeyCompassHeading.create().listen(this) { heading ->
            publish { it.copy(heading = heading) }
        }
        FlightControllerKey.KeyAircraftVelocity.create().listen(this) { velocity ->
            publish { it.copy(velocityX = velocity?.x, velocityY = velocity?.y, velocityZ = velocity?.z) }
        }
    }

    fun stopListening() {
        KeyManager.getInstance().cancelListen(this)
    }
}
