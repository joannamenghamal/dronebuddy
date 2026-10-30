package com.example.dronebuddyapp.dronecontrollers

import android.content.Context
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.asLiveData
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory


class DroneManagerViewModel(
    appContext : Context
) : ViewModel() {

    val droneManager = DroneManager(appContext)

    val droneAppConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.appRegisterStatus.asLiveData()

    val droneConnectionStatus: LiveData<Boolean> =
        droneManager.droneConnectionControl.droneConnectionStatus.asLiveData()


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