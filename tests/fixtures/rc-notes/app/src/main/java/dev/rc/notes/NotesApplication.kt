package dev.rc.notes

import android.app.Application

class NotesApplication : Application() {
    val repository = NotesRepository()
}
