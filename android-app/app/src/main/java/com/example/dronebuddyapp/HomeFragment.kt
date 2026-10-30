package com.example.dronebuddyapp

import android.graphics.Color
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.activityViewModels
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel
import com.example.dronebuddyapp.logcontent.LogItem

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

        // Find TextViews
        val updatableAppConnectionStatus = view.findViewById<TextView>(R.id.updatable_dji_app_connection_status)
        val updatableDroneConnectionStatus = view.findViewById<TextView>(R.id.updatable_dji_drone_connection_status)

        // Connect up buttons
        retryAppConnection(btnRetryAppConnection)
        retryDroneConnection(btnRetryDroneConnection)

        // Connect up TextViews
        connectAppConnectionText(updatableAppConnectionStatus)
        connectDroneConnectionText(updatableDroneConnectionStatus)
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


}