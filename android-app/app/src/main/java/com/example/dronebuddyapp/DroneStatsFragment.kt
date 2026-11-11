package com.example.dronebuddyapp

import android.graphics.Color
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.core.graphics.toColorInt
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel
import dji.sdk.keyvalue.value.flightcontroller.CompassCalibrationState
import kotlin.collections.emptyMap
import kotlin.getValue

// TODO: Rename parameter arguments, choose names that match
// the fragment initialization parameters, e.g. ARG_ITEM_NUMBER
private const val ARG_PARAM1 = "param1"
private const val ARG_PARAM2 = "param2"

/**
 * A simple [Fragment] subclass.
 * Use the [DroneStatsFragment.newInstance] factory method to
 * create an instance of this fragment.
 */
class DroneStatsFragment : Fragment() {
    // TODO: Rename and change types of parameters
    private var param1: String? = null
    private var param2: String? = null

    // Get DroneManagerViewModel
    private val droneManagerViewModels : DroneManagerViewModel by activityViewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        arguments?.let {
            param1 = it.getString(ARG_PARAM1)
            param2 = it.getString(ARG_PARAM2)
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate the layout for this fragment
        return inflater.inflate(R.layout.fragment_drone_stats, container, false)
    }

    // Define button functionality below for this page
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // List of alerts that we will update with alerts
        val alertTextView = view.findViewById<TextView>(R.id.alertEmptyText)
        val _alerts = MutableLiveData<Map<String, Alert>>(emptyMap<String, Alert>())
        val alerts : LiveData<Map<String, Alert>> = _alerts
        connectAlerts(alertTextView, _alerts, alerts)

        // Define TextView Stats
        val tvBatteryStatus = view.findViewById<TextView>(R.id.statBattery)
        val tvSpeedStatus = view.findViewById<TextView>(R.id.statSpeed)
        val tvAltitudeStatus = view.findViewById<TextView>(R.id.statAltitude)
        val tvCompassCalibrationStatus = view.findViewById<TextView>(R.id.statCompassCalibration)

        // Define Buttons
        val btnCompassCalibration = view.findViewById<Button>(R.id.btnCompassCalibration)

        // Connect Status'
        connectBatteryStatus(tvBatteryStatus)
        connectSpeedStatus(tvSpeedStatus)
        connectAltitudeStatus(tvAltitudeStatus)
        connectCompassCalibrationStatus(tvCompassCalibrationStatus)

        // Connect Buttons
        activateCompassCalibrationStatus(btnCompassCalibration)
        connectButtonCompassCalibrationStatus(btnCompassCalibration)
    }

    private fun renderAlertText(tv: TextView, alerts: Collection<Alert>) {
        if (alerts.isEmpty()) {
            tv.text = "✓ All systems normal"
            tv.setTextColor(Color.GREEN)
        } else {
            tv.text = alerts.joinToString("\n") { "⚠ ${it.message}" }
            tv.setTextColor("#ff4c40".toColorInt())
        }
    }


    // Passes the alertList to be edited, and uses the alertLiveData to track
    private fun connectAlerts(tv: TextView, alertList : MutableLiveData<Map<String, Alert>>, alertLiveData: LiveData<Map<String, Alert>>) {
        trackCompassCalibration(alertList)
        alertLiveData.observe(viewLifecycleOwner) {
            map ->
            renderAlertText(tv, map.values)
        }
    }

    private fun trackCompassCalibration(alertList : MutableLiveData<Map<String, Alert>>) {
        droneManagerViewModels.droneCompassCalibrationStatusEnum.observe(viewLifecycleOwner) {
                status ->
            if (
                status != CompassCalibrationState.SUCCEEDED && status != CompassCalibrationState.IDLE
            ) {
                var currList = alertList.value ?: emptyMap<String, Alert>()
                alertList.value = currList + ("CompassCalib" to Alert("Compass Uncalibrated! Drone will not fly!", AlertType.CRITICAL))
            }
            else {
                val currList = alertList.value ?: emptyMap<String, Alert>()
                alertList.value = currList - "CompassCalib"
            }
        }
    }

    private enum class AlertType(val colorInt : Int) {
        WARNING("#E9D502".toColorInt()),
        CRITICAL("#ff4c40".toColorInt())
    }
    private data class Alert(val message: String, val alertType: AlertType)

    private fun connectBatteryStatus(tv: TextView) {
        droneManagerViewModels.droneBatteryStatus.observe(viewLifecycleOwner) {
            battPercentage ->
            tv.text = battPercentage.toString()
        }
    }
    private fun connectSpeedStatus(tv: TextView) {
        droneManagerViewModels.droneSpeedStatus.observe(viewLifecycleOwner) {
            speedStatus ->
            tv.text = speedStatus.toString()
        }
    }
    private fun connectAltitudeStatus(tv: TextView) {
        droneManagerViewModels.droneAltitudeStatus.observe(viewLifecycleOwner) {
                altitudeStatus ->
            tv.text = altitudeStatus.toString()
        }
    }

    private fun connectCompassCalibrationStatus(tv: TextView) {
        droneManagerViewModels.droneCompassCalibrationStatus.observe(viewLifecycleOwner) {
            status ->
            tv.text = status
        }
    }

    private fun activateCompassCalibrationStatus(btn: Button) {
        btn.setOnClickListener {
            val droneFlightKeys = droneManagerViewModels.droneManager.droneFlightKeys
            val droneFlightKeysEnum = droneManagerViewModels.droneManager.droneFlightKeys.droneCalibrationStatusEnum.value
            // First check to see if currently in calibration mode, by checking if text is succeed or failed
            // We will check the enum since that is consistent
                if (
                    droneFlightKeysEnum == CompassCalibrationState.IDLE ||
                    droneFlightKeysEnum == CompassCalibrationState.SUCCEEDED ||
                    droneFlightKeysEnum == CompassCalibrationState.FAILED ||
                    droneFlightKeysEnum == CompassCalibrationState.UNKNOWN
                ) {
                    droneFlightKeys.activateDroneCompassCalibration()
                }
                else {
                    droneFlightKeys.cancelDroneCompassCalibration()
                }

        }
    }

    private fun connectButtonCompassCalibrationStatus(btn: Button) {
        // We also want to connect the button so that it changes text based on whether it is going to
        // cancel calibration or if it will start calib
        droneManagerViewModels.droneCompassCalibrationStatusEnum.observe(viewLifecycleOwner) {
                status ->
            if (
                status == CompassCalibrationState.IDLE ||
                status == CompassCalibrationState.SUCCEEDED ||
                status == CompassCalibrationState.FAILED ||
                status == CompassCalibrationState.UNKNOWN
            ) {
                btn.text = "Activate Drone Calibration?"
            }
            else {
                btn.text = "Cancel Drone Calibration?"
            }
        }
    }


    companion object {
        /**
         * Use this factory method to create a new instance of
         * this fragment using the provided parameters.
         *
         * @param param1 Parameter 1.
         * @param param2 Parameter 2.
         * @return A new instance of fragment DroneStatsFragment.
         */
        // TODO: Rename and change types and number of parameters
        @JvmStatic
        fun newInstance(param1: String, param2: String) =
            DroneStatsFragment().apply {
                arguments = Bundle().apply {
                    putString(ARG_PARAM1, param1)
                    putString(ARG_PARAM2, param2)
                }
            }
    }
}