package com.example.lightweight

import android.app.Application
import com.example.lightweight.image.AppImages
import com.example.lightweight.logging.AppLogger
class StackApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        AppImages.initialize(this)
        AppLogger.initialize(BuildConfig.DEBUG)
    }
}
