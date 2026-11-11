package com.example.dronebuddyapp.logcontent

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.dronebuddyapp.databinding.FragmentLogBinding

/**
 * Using a listadapter instead of recyclerviewadapter since it automatically updates using DIFFutil
 */
class LogListAdapterView() : ListAdapter<LogItem.LogItem, LogListAdapterView.ViewHolder>(DIFF) {

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
        val item = getItem(position)
        holder.idView.text = "${item.formattedTime} - [${item.tag}]"
        holder.idView.setTextColor(item.status.color)
        holder.contentView.text = item.content
        holder.contentView.setTextColor(item.status.color)
    }

    inner class ViewHolder(binding: FragmentLogBinding) : RecyclerView.ViewHolder(binding.root) {
        val idView: TextView = binding.itemNumber
        val contentView: TextView = binding.content

        override fun toString(): String {
            return super.toString() + " '" + contentView.text + "'"
        }
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<LogItem.LogItem>() {
            override fun areItemsTheSame(a: LogItem.LogItem, b: LogItem.LogItem) = a === b
            override fun areContentsTheSame(a: LogItem.LogItem, b: LogItem.LogItem) = a == b
        }
    }

}