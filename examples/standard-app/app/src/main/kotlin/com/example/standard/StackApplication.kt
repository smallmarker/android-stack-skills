package com.example.standard

import android.app.Application
import com.example.standard.image.AppImages
import com.example.standard.logging.AppLogger
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class StackApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        AppImages.initialize(this)
        AppLogger.initialize(BuildConfig.DEBUG)
    }
}
