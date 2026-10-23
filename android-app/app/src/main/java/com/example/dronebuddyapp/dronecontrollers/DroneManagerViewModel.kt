package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory


class DroneManagerViewModel(
    appContext : Context
) : ViewModel() {

    val droneManager = DroneManager(appContext)

    // Factory as a companion object
    companion object {

        val appContextKey = CreationExtras.Key<Context>()

        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val appContext = checkNotNull(this[appContextKey])
                DroneManagerViewModel(
                    appContext = appContext
                )
            }
        }
    }
}