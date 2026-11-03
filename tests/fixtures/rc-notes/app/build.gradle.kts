plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "dev.rc.notes"
    compileSdk = 36
    defaultConfig { applicationId = "dev.rc.notes"; minSdk = 26; targetSdk = 36; versionCode = 1; versionName = "1.0" }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { jvmToolchain(17) }
dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.material3)
    implementation(libs.activity)
    testImplementation(libs.junit)
}
