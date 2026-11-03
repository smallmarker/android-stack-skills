package com.example.standard

import com.example.standard.data.DefaultHomeRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class HomeRepositoryTest {
    @Test fun greeting() = runBlocking {
        assertEquals("Your app is ready.", DefaultHomeRepository().greeting())
    }
}
