package com.example.lightweight

import com.example.lightweight.data.HomeRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class HomeRepositoryTest {
    @Test fun greeting() = runBlocking {
        assertEquals("Your app is ready.", HomeRepository().greeting())
    }
}
