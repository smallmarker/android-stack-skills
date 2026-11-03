package dev.rc.notes

import org.junit.Assert.assertEquals
import org.junit.Test

class NotesRepositoryTest {
    @Test fun existingBusinessBehavior() {
        assertEquals(listOf("First independent note", "Keep existing code"), NotesRepository().titles())
    }
}
