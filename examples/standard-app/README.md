# StandardDemo

Generated with Android Stack Skills Standard (Hilt) preset.

Requires JDK 17 and Android SDK platform 36. Set ANDROID_HOME or your own untracked local.properties.

```sh
./gradlew :app:assembleDebug :app:testDebugUnitTest
```

Open this directory in Android Studio. Run app on API 26+.
The home screen is local and works without a backend. Replace example.com and the example UserApi contract before making live requests.
See app/android-stack/{network,image,logging}/Usage.md for Recipe APIs.
StateFlow lives in ui/HomeViewModel, data access in data/HomeRepository.
Never pass secrets or personal data to logging messages. Release facade logging is disabled.
