package com.example.dronebuddyapp

import android.graphics.Color
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.graphics.toColorInt
import androidx.fragment.app.activityViewModels
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel
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

        // Define TextView Stats
        val tvBatteryStatus = view.findViewById<TextView>(R.id.statBattery)
        val tvSpeedStatus = view.findViewById<TextView>(R.id.statSpeed)
        val tvAltitudeStatus = view.findViewById<TextView>(R.id.statAltitude)
        val tvCompassCalibrationStatus = view.findViewById<TextView>(R.id.statCompassCalibration)

        // Connect Status'
        connectBatteryStatus(tvBatteryStatus)
        connectSpeedStatus(tvSpeedStatus)
        connectAltitudeStatus(tvAltitudeStatus)
        connectCompassCalibrationStatus(tvCompassCalibrationStatus)
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