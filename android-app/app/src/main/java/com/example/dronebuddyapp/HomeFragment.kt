package com.example.dronebuddyapp

import android.graphics.Color
import android.os.Bundle
import android.util.Log
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.activityViewModels
import com.example.dronebuddyapp.dronecontrollers.DjiVirtualStickController
import com.example.dronebuddyapp.dronecontrollers.DroneManager
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel
import com.example.dronebuddyapp.logcontent.LogItem
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.sdk.keyvalue.value.common.EmptyMsg
import dji.sdk.keyvalue.value.common.Velocity3D
import dji.v5.common.callback.CommonCallbacks

// TODO: Rename parameter arguments, choose names that match
// the fragment initialization parameters, e.g. ARG_ITEM_NUMBER
private const val ARG_PARAM1 = "param1"
private const val ARG_PARAM2 = "param2"

/**
 * A simple [Fragment] subclass.
 * Use the [HomeFragment.newInstance] factory method to
 * create an instance of this fragment.
 */
class HomeFragment : Fragment() {
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
        return inflater.inflate(R.layout.fragment_home, container, false)
    }

    companion object {
        /**
         * Use this factory method to create a new instance of
         * this fragment using the provided parameters.
         *
         * @param param1 Parameter 1.
         * @param param2 Parameter 2.
         * @return A new instance of fragment HomeFragment.
         */
        // TODO: Rename and change types and number of parameters
        @JvmStatic
        fun newInstance(param1: String, param2: String) =
            HomeFragment().apply {
                arguments = Bundle().apply {
                    putString(ARG_PARAM1, param1)
                    putString(ARG_PARAM2, param2)
                }
            }
    }

    // Define button functionality below for this page
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Define buttons
        val btnRetryAppConnection = view.findViewById<Button>(R.id.btn_connect_app_retry)
        val btnRetryDroneConnection = view.findViewById<Button>(R.id.btn_connect_drone_retry)
        val btnLiftoffLandingActivate = view.findViewById<Button>(R.id.btn_liftoff_landing)
        val btnChangeVirtualStickMode = view.findViewById<Button>(R.id.btn_change_virtual_stickmode)

        // Find TextViews
        val updatableAppConnectionStatus = view.findViewById<TextView>(R.id.updatable_dji_app_connection_status)
        val updatableDroneConnectionStatus = view.findViewById<TextView>(R.id.updatable_dji_drone_connection_status)
        val updatableLiftoffLandingStatus = view.findViewById<TextView>(R.id.updatable_liftoff_landing_status)
        val updatableVirtualStickModeStatus = view.findViewById<TextView>(R.id.updatable_virtual_stickmode_status)

        // Connect up buttons
        retryAppConnection(btnRetryAppConnection)
        retryDroneConnection(btnRetryDroneConnection)
        activateLiftoffLanding(btnLiftoffLandingActivate)
        connectDroneInAirButtonStatus(btnLiftoffLandingActivate)
        activateVirtualStickMode(btnChangeVirtualStickMode)
        connectVirtualStickModeButtonStatus(btnChangeVirtualStickMode)


        // Connect up TextViews
        connectAppConnectionText(updatableAppConnectionStatus)
        connectDroneConnectionText(updatableDroneConnectionStatus)
        connectDroneInAirStatus(updatableLiftoffLandingStatus)
        connectVirtualStickModeStatus(updatableVirtualStickModeStatus)
    }


    private fun retryAppConnection(btn: Button) {
        btn.setOnClickListener {
            val appStatus = droneManagerViewModels.droneAppConnectionStatus

            // Add a popup thing for warnings/errors
            if (appStatus.value == true) {
                LogItem.addLog("DJI App Connection", "App is already connected!", LogItem.Status.WARNING)
            }
            else {
                LogItem.addLog("DJI App Connection", "Retrying App Connection", LogItem.Status.INFO)
            }
        }

    }

    private fun retryDroneConnection(btn: Button) {
        btn.setOnClickListener {
            val droneStatus = droneManagerViewModels.droneConnectionStatus

            // Add a popup thing for warnings/errors
            if (droneStatus.value == true) {
                LogItem.addLog("DJI App Connection", "Drone is already connected!", LogItem.Status.WARNING)
            }
            else {
                LogItem.addLog("DJI App Connection", "Retrying Drone Connection", LogItem.Status.INFO)
            }

//            droneManagerViewModels.droneManager.droneConnectionControl.debugSetAppConnectionFalse()
//            LogItem.addLog("DJI App Connection", "Status set to false!", LogItem.Status.ERROR)
        }


    }

    // keyManager.getValue(KeyTools.createKey(FlightControllerKey.KeyAircraftVelocity))
//    var aircraftVelocity = object: CommonCallbacks.KeyListener<Velocity3D> {
//        override fun onValueChange(p0: Velocity3D?, p1: Velocity3D?) {
//            TODO("Not yet implemented")
//        }
//    }

    private fun activateLiftoffLanding(btn: Button) {
        val flightKeyController = droneManagerViewModels.droneManager.droneFlightKeys

        // This is passed as the btn.post so that the update of the visuals is done in the ui thread
        // This prevents any crashes due to how sdk thread runs differently
        fun enableButton() {
            btn.post {
                btn.isEnabled = true
            }
        }
        btn.setOnClickListener {
            // Change buttons to say Land, and change function to landing
            // Probably pass disable buttons and pass into lambda a reenable when it is done
            // We want to reenable the button no matter what if it fails or succeeds to prevent softlocks
            if (droneManagerViewModels.droneInAirStatus.value == true) {
                flightKeyController.activateDroneLanding({enableButton()}, {enableButton()})
                btn.isEnabled = false
            }
            else {
                flightKeyController.activateDroneLiftoff({enableButton()}, {enableButton()})
                btn.isEnabled = false
            }

        }
    }

    private fun activateVirtualStickMode(btn: Button) {
        val virtStick = droneManagerViewModels.droneManager.virtualStick

        btn.setOnClickListener {
            // True means Enabled, so we need to disable
            if (droneManagerViewModels.virtualStickEnableStatus.value == true) {
                virtStick.disable { success ,error ->
                    if (success) {
                        LogItem.addLog("Virtual Stick Override", "Successfully Disabled Virtual Stick Mode", LogItem.Status.INFO)
                    }
                    else {
                        LogItem.addLog("Virtual Stick Override", "Failed to Disable Virtual Stick Mode", LogItem.Status.ERROR)
                    }

                }
            }
            else {
                virtStick.enable { success, error ->
                    if (success) {
                        LogItem.addLog("Virtual Stick Override", "Successfully Enabled Virtual Stick Mode", LogItem.Status.INFO)
                    }
                    else {
                        LogItem.addLog("Virtual Stick Override", "Failed to Enable Virtual Stick Mode", LogItem.Status.ERROR)
                    }
                }
            }
        }
    }

    // Look into DroneManagerViewModel for livedata
    private fun connectAppConnectionText(tv: TextView) {
        droneManagerViewModels.droneAppConnectionStatus.observe(viewLifecycleOwner) {
            connected ->
            tv.text = if (connected) "Connected" else "Disconnected"
            tv.setTextColor(if (connected) Color.GREEN else Color.RED)
        }

    }

    private fun connectDroneConnectionText(tv: TextView) {
        droneManagerViewModels.droneConnectionStatus.observe(viewLifecycleOwner) {
            connected ->
            tv.text = if (connected) "Connected" else "Disconnected"
            tv.setTextColor(if (connected) Color.GREEN else Color.RED)
        }
    }

    private fun connectDroneInAirStatus(tv: TextView) {
        droneManagerViewModels.droneInAirStatus.observe(viewLifecycleOwner) {
            connected ->
            tv.text = if (connected) "Flying" else "Grounded"
            tv.setTextColor(if (connected) Color.GREEN else Color.RED)
        }
    }

    private fun connectVirtualStickModeStatus(tv: TextView) {
        droneManagerViewModels.virtualStickEnableStatus.observe(viewLifecycleOwner) {
                connected ->
            tv.text = if (connected) "Enabled" else "Disabled"
            tv.setTextColor(if (connected) Color.GREEN else Color.RED)
        }
    }

    private fun connectDroneInAirButtonStatus(btn: Button) {
        droneManagerViewModels.droneInAirStatus.observe(viewLifecycleOwner) {
            connected ->
            // True means In Air
            btn.text = if (connected) "Activate Landing?" else "Activate Liftoff?"
        }
    }

    private fun connectVirtualStickModeButtonStatus(btn: Button) {
        droneManagerViewModels.virtualStickEnableStatus.observe(viewLifecycleOwner) {
                connected ->
            // True means virtual stick mode is enabled
            btn.text = if (connected) "Disable Virtual Stick Mode?" else "Enable Virtual Stick Mode?"
        }
    }





}