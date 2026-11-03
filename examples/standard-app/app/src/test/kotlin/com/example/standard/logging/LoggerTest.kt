package com.example.standard.logging

import org.junit.Assert.*
import org.junit.Test
import timber.log.Timber

class LoggerTest {
    @Test fun releaseIsSilent() {
        val messages = mutableListOf<String>()
        val capture = object : Timber.Tree() {
            override fun log(priority: Int, tag: String?, message: String, t: Throwable?) { messages += message }
        }
        Timber.plant(capture)
        try {
            AppLogger.initialize(false)
            AppLogger.e("Auth", "Request failed", IllegalStateException("secret"))
            AppLogger.event("Home", "page.created", listOf(LogField.Redacted))
            AppLogger.event("Home", "invalid event must be a no-op in release")
            assertTrue(messages.isEmpty())
        } finally { Timber.uproot(capture) }
    }

    @Test fun debugLogsExcludeExceptionDetails() {
        val messages = mutableListOf<String>()
        val capture = object : Timber.Tree() {
            override fun log(priority: Int, tag: String?, message: String, t: Throwable?) { messages += message }
        }
        try {
            AppLogger.initialize(true, capture)
            AppLogger.e("Network", "Request failed", IllegalStateException("secret-token"))
            assertEquals(listOf("Request failed [IllegalStateException]"), messages)
        } finally { AppLogger.initialize(false) }
    }

    @Test fun structuredFieldDoesNotContainSecret() {
        assertEquals("Redacted", LogField.Redacted.toString())
        val sink = object : Timber.Tree() {
            override fun log(priority: Int, tag: String?, message: String, t: Throwable?) = Unit
        }
        try {
            AppLogger.initialize(true, sink)
            assertThrows(IllegalArgumentException::class.java) { AppLogger.event("Auth", "token secret") }
        } finally { AppLogger.initialize(false) }
    }
}
