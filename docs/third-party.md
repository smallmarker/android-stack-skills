# Third-party provenance

Original Python/Kotlin integration code and Skills: MIT, project LICENSE.

No Retrofit, OkHttp, Coil, Timber, Hilt, Gson, Coroutines or AndroidX implementation source is vendored. Recipe `source.copied_source` lists are empty. Dependency binaries are resolved by the user's Gradle installation. Those projects use Apache-2.0; consult their upstream repositories and resolved artifacts for complete notices and transitive licensing. JUnit 4.13.2 is a test-only EPL-1.0 dependency.

The one redistributed binary is Gradle 8.14.3's official `gradle-wrapper.jar`, from https://raw.githubusercontent.com/gradle/gradle/v8.14.3/gradle/wrapper/gradle-wrapper.jar. Its hash is pinned in generator.py and compatibility.md. Gradle's upstream complete LICENSE (including relevant third-party license text) is bundled at src/android_stack_skills/data/licenses/Gradle-LICENSE.txt and copied into every generated gradle/wrapper directory. The v8.14.3 root has no separate NOTICE file at the requested URL (HTTP 404); no nonexistent notice is fabricated.

Upstream sources: [Gradle](https://github.com/gradle/gradle/tree/v8.14.3), [Retrofit](https://github.com/square/retrofit), [OkHttp](https://github.com/square/okhttp), [Coil](https://github.com/coil-kt/coil), [Timber](https://github.com/JakeWharton/timber), [Hilt](https://github.com/google/dagger), [Gson](https://github.com/google/gson), [Coroutines](https://github.com/Kotlin/kotlinx.coroutines), [JUnit](https://github.com/junit-team/junit4).


The Glide Recipe references the Maven dependency at 4.16.0. Its original wrapper and tests use the project MIT license. Glide has a BSD-2-Clause primary license with separate notices for bundled components. [Glide upstream license](https://github.com/bumptech/glide/blob/v4.16.0/LICENSE)
