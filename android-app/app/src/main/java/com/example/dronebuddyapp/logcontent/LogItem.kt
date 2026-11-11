package com.example.dronebuddyapp.logcontent

import android.graphics.Color
import android.util.Log
import androidx.core.graphics.toColorInt
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.text.SimpleDateFormat
import java.util.ArrayList
import java.util.Date
import java.util.HashMap
import java.util.Locale

/**
 * Helper class for providing sample content for user interfaces created by
 * Android template wizards.
 *
 * TODO: Replace all uses of this class before publishing your app.
 */
object LogItem {

    private val _logs = MutableStateFlow<List<LogItem>>(emptyList())
    val logs : StateFlow<List<LogItem>> = _logs.asStateFlow()

    enum class Status (val status : String, val color: Int) {
        INFO("INFO", Color.BLACK),

        // Mustard Warning Color
        WARNING("WARNING", "#FFBA00".toColorInt()),
        ERROR("ERROR", Color.RED),
    }

    init {
        // Add some sample items.
        addLog("Test", "Hello this is a test", Status.INFO)
    }

    // This is how people will add to our log
    fun addLog(tag: String, content: String, status: LogItem.Status) {
        val createdLogItem = LogItem(tag, content, status)
        _logs.update {
            (it + createdLogItem).takeLast(1000) // Only grab last 1000 logs
        }
        Log.d(tag, content)
    }


    // Actual data class that we use to display
    data class LogItem(val tag: String, val content: String, val status: Status) {

        // Get the current local time
        val formattedTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        override fun toString(): String = content
    }
}