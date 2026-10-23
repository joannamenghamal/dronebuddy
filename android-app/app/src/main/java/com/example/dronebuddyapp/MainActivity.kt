package com.example.dronebuddyapp

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.drawerlayout.widget.DrawerLayout
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentContainerView
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.MutableCreationExtras
import com.example.dronebuddyapp.dronecontrollers.DroneManager
import com.example.dronebuddyapp.dronecontrollers.DroneManagerViewModel

class MainActivity : AppCompatActivity() {
    private lateinit var droneManagerViewModel : DroneManagerViewModel
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContentView(R.layout.activity_main)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.drawerLayout)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // https://developer.android.com/topic/libraries/architecture/viewmodel/viewmodel-factories?
        Log.d("Creating VM","App Context: " + applicationContext.toString())
        val extras = MutableCreationExtras().apply {
            set(DroneManagerViewModel.appContextKey, applicationContext)
        }

        droneManagerViewModel = ViewModelProvider.create(
            this,
            factory = DroneManagerViewModel.Factory,
            extras = extras
        )[DroneManagerViewModel::class.java]

        // Initialize the drone manager
        // val droneManager = DroneManager(applicationContext)
        droneManagerViewModel = ViewModelProvider.create(
            this,
            factory = DroneManagerViewModel.Factory,
            extras = extras
        )[DroneManagerViewModel::class.java]
        // Get fragmentContainerView
        val mainFragmentContainerView = findViewById<FragmentContainerView>(R.id.mainFragmentContainerView)
        showFragmentOnMain(HomeFragment(), "Home")

        // Add button functionality
        val menuButton = findViewById<ImageButton>(R.id.btnMenu)
        val drawerLayout = findViewById<DrawerLayout>(R.id.drawerLayout)

        // Menu Button
        menuButton.setOnClickListener {
            if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                drawerLayout.closeDrawer(GravityCompat.START)
            }
            else {
                drawerLayout.openDrawer(GravityCompat.START)
            }
        }

        // Side Bar Buttons
        // Switch Fragments
        val btnHome = findViewById<Button>(R.id.btnHome)
        val btnCameraView = findViewById<Button>(R.id.btnCameraView)
        val btnDroneStats = findViewById<Button>(R.id.btnDroneStats)
        btnSetFragment(btnHome, HomeFragment(), "Home")
        btnSetFragment(btnCameraView, CameraViewFragment(), "Camera View")
        btnSetFragment(btnDroneStats, DroneStatsFragment(), "Drone Stats")
    }

    private fun showFragmentOnMain(fragment: Fragment, title: String) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.mainFragmentContainerView, fragment)
            .commit()

        val topBarText = findViewById<TextView>(R.id.tvToolbarTitle)
        topBarText.text = title


        findViewById<DrawerLayout>(R.id.drawerLayout)
            .closeDrawer(GravityCompat.START)
    }

    private fun btnSetFragment(btn: Button, fragment: Fragment, title: String) {
        btn.setOnClickListener {
            showFragmentOnMain(fragment, title)
        }
    }
}

