package com.example.dronebuddyapp.logcontent

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.example.dronebuddyapp.databinding.FragmentLogBinding

/**
 * [androidx.recyclerview.widget.RecyclerView.Adapter] that can display a [LogItem.LogItem].
 * TODO: Replace the implementation with code for your data type.
 */
class LogRecyclerViewAdapter(
    private val values: List<LogItem.LogItem>
) : RecyclerView.Adapter<LogRecyclerViewAdapter.ViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {

        return ViewHolder(
            FragmentLogBinding.inflate(
                LayoutInflater.from(parent.context),
                parent,
                false
            )
        )

    }

    // This changes what is actually displayed
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = values[position]
        holder.idView.text = "${item.formattedTime} - [${item.tag}]"
        holder.contentView.text = item.content
    }

    override fun getItemCount(): Int = values.size

    inner class ViewHolder(binding: FragmentLogBinding) : RecyclerView.ViewHolder(binding.root) {
        val idView: TextView = binding.itemNumber
        val contentView: TextView = binding.content

        override fun toString(): String {
            return super.toString() + " '" + contentView.text + "'"
        }
    }

}