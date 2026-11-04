from pathlib import Path
import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path/'settings.gradle.kts').write_text('include(":app")\n')
    (tmp_path/'app/src/main/java/com/example/demo').mkdir(parents=True)
    (tmp_path/'app/src/main/AndroidManifest.xml').write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><uses-permission android:name="android.permission.INTERNET"/><application/></manifest>')
    (tmp_path/'app/build.gradle.kts').write_text('plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }\nandroid { namespace = "com.example.demo"\n defaultConfig { minSdk = 26 }\n buildFeatures { compose = true } }\ndependencies {}\n')
    (tmp_path/'build.gradle.kts').write_text(
        'plugins { id("com.android.application") version "8.13.1" apply false; '
        'id("org.jetbrains.kotlin.android") version "2.2.20" apply false }\n'
    )
    wrapper = tmp_path/'gradle/wrapper'
    wrapper.mkdir(parents=True)
    (wrapper/'gradle-wrapper.properties').write_text(
        'distributionUrl=https://services.gradle.org/distributions/gradle-8.14.3-bin.zip\n'
    )
    return tmp_path
