package com.example.dronebuddyapp.logcontent

import android.graphics.Color
import android.util.Log
import androidx.core.graphics.toColorInt
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

    enum class Status (val status : String, val color: Int) {
        INFO("INFO", Color.BLACK),

        // Mustard Warning Color
        WARNING("WARNING", "#FFBA00".toColorInt()),
        ERROR("ERROR", Color.RED),
    }

    /**
     * An array of sample (placeholder) items.
     */
    val ITEMS: MutableList<LogItem> = ArrayList()

    /**
     * A map of sample (placeholder) items, by tag.
     */
    val ITEM_MAP: MutableMap<String, LogItem> = HashMap()

    private val COUNT = 25

    // Definitely need to remove this
    init {
        // Add some sample items.
        addItem(LogItem("Tag1", "Hello this is a test", Status.INFO))

    }

    // This is how people will add to our log
    fun addLog(tag: String, content: String, status: LogItem.Status) {
        val createdLogItem = LogItem(tag, content, status)

        addItem(createdLogItem)
        Log.d(tag, content)
    }

    private fun addItem(item: LogItem) {
        ITEMS.add(item)
        ITEM_MAP.put(item.tag, item)
    }

    /**
     * A placeholder item representing a piece of content.
     */
    data class LogItem(val tag: String, val content: String, val status: Status) {

        // Get the current local time
        val formattedTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        override fun toString(): String = content
    }
}