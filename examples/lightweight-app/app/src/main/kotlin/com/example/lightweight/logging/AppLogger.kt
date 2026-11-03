package com.example.lightweight.logging

import timber.log.Timber

/** Numeric fields are typed. Credentials and personal data have no field representation. */
sealed interface LogField {
    data class Count(val value: Int) : LogField
    data class DurationMs(val value: Long) : LogField
    data class StatusCode(val value: Int) : LogField
    data object Redacted : LogField
}

interface Logger {
    fun event(tag: String, event: String, fields: List<LogField> = emptyList())
}

object AppLogger : Logger {
    @Volatile private var debug = false
    private var tree: Timber.Tree? = null

    /** Pass the application variant's BuildConfig.DEBUG; release defaults to silent. */
    @Synchronized fun initialize(isDebug: Boolean, debugTree: Timber.Tree = Timber.DebugTree()) {
        debug = isDebug
        tree?.let(Timber::uproot)
        tree = if (isDebug) debugTree.also(Timber::plant) else null
    }

    private fun write(priority: Int, tag: String, message: String, throwable: Throwable? = null) {
        if (!debug) return
        // Throwable.message and stack traces may contain URLs, credentials, or personal data.
        val errorType = throwable?.let { " [${it.javaClass.simpleName}]" }.orEmpty()
        Timber.tag(tag.take(23)).log(priority, "%s", message + errorType)
    }

    /** Static developer-authored messages only. Never interpolate user/server content. */
    fun d(tag: String, message: String) = write(3, tag, message)
    fun i(tag: String, message: String) = write(4, tag, message)
    fun w(tag: String, message: String) = write(5, tag, message)
    fun e(tag: String, message: String, throwable: Throwable? = null) = write(6, tag, message, throwable)

    override fun event(tag: String, event: String, fields: List<LogField>) {
        if (!debug) return
        require(event.matches(Regex("[A-Za-z][A-Za-z0-9_.-]{0,63}")))
        d(tag, "$event ${fields.joinToString()}")
    }
}
