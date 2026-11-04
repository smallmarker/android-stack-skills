# Compatibility

This page tracks Android tooling and dependency compatibility. See [Agent compatibility](agent-compatibility.md) for installer and host runtime evidence.

Version audit and validation date: **2026-11-02**. Newest stable does not automatically become the tested baseline. The older stable pins below deliberately retain AGP 8 / explicit Kotlin Android support and OkHttp 4 APIs. Existing versions are never silently replaced.

| Component | Fixed V1 baseline | Newest stable observed | Primary source |
|---|---|---|---|
| AGP | 8.13.1 | 9.5.0 | [Google metadata](https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml), [AGP 8.13 compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes) |
| Gradle | 8.14.3 | 9.8.2 | [current release metadata](https://services.gradle.org/versions/current), [distribution and checksum](https://services.gradle.org/distributions/), [release](https://docs.gradle.org/8.14.3/release-notes.html) |
| Kotlin | 2.2.20 | 2.4.21 | [metadata](https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml) |
| Compose BOM | 2025.08.01 | 2026.09.00 | [Google metadata](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml) |
| Hilt | 2.57.2, kapt | 2.60.1 | [metadata](https://repo.maven.apache.org/maven2/com/google/dagger/hilt-android/maven-metadata.xml), [releases](https://github.com/google/dagger/releases) |
| Retrofit / Gson converter | 3.0.0 | 3.0.0 | [metadata](https://repo.maven.apache.org/maven2/com/squareup/retrofit2/retrofit/maven-metadata.xml) |
| OkHttp / MockWebServer | 4.12.0 | 5.5.1 | [metadata](https://repo.maven.apache.org/maven2/com/squareup/okhttp3/okhttp/maven-metadata.xml) |
| Coil | 3.3.0 | 3.6.3 | [metadata](https://repo.maven.apache.org/maven2/io/coil-kt/coil3/coil-compose/maven-metadata.xml), [changelog](https://coil-kt.github.io/coil/changelog/) |
| Timber | 5.0.1 | 5.0.1 | [metadata](https://repo.maven.apache.org/maven2/com/jakewharton/timber/timber/maven-metadata.xml) |
| kotlinx Serialization | not installed; Gson selected | 1.12.0 | [metadata](https://repo.maven.apache.org/maven2/org/jetbrains/kotlinx/kotlinx-serialization-json/maven-metadata.xml) |
| Gson | 2.13.1 | not used as an upgrade target | [upstream](https://github.com/google/gson/releases/tag/gson-parent-2.13.1) |
| Coroutines | 1.10.2 | not used as an upgrade target | [upstream](https://github.com/Kotlin/kotlinx.coroutines/releases/tag/1.10.2) |
| Activity / Lifecycle | 1.10.1 / 2.9.2 | not used as upgrade targets | [AndroidX releases](https://developer.android.com/jetpack/androidx/releases) |

AGP 8.13 requires Gradle >=8.13 and JDK 17. Our generated combination uses Gradle 8.14.3, Java 17, compile/target SDK 36, minSdk 26, Compose with Kotlin Compose plugin 2.2.20. The complete Lightweight and Standard combinations passed actual assembleDebug and testDebugUnitTest. Recipe standalone minimum is API 21; that floor has not been runtime-tested on API 21 devices.

Test machine: macOS arm64, Python 3.11.14, JDK Microsoft OpenJDK 17.0.15, Android SDK Platform 36. The wrapper came from the official Gradle v8.14.3 repository; JAR SHA-256 `7d3a4ac4de1c32b59bc6a4eb8ecb8e612ccd0cf1ae1e99f66902da64df296172`; distribution SHA-256 `bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531`.

Google Maven connections required the machine's proxy for JVM builds. Proxy flags were set only in test processes. No proxy, SDK path or credentials are generated into projects. `scripts/check_versions.py` re-reads upstream metadata without mutating pins; Python HTTPS occasionally reset on Google Maven, so those entries were confirmed using curl.

Unsupported automatic writes: Groovy DSL, AGP 9 built-in Kotlin, dependency bundles/dynamic expressions, custom module mappings/includeBuild, complex convention plugins, KMP, automatic dependency upgrades and existing ImageLoader merging. The general Recipe baseline still gates Kotlin below 2.2.20 and AGP below 8.13. Retrofit uses the exact toolchain profiles below.

At RC 2026-11-03, Network and Logging Recipes are 0.1.1; Coil and the two presets remain 0.1.0. Dependency pins are unchanged. Every Recipe records its upstream version/license. Kotlin wrappers are original project source; no upstream library implementation is copied. Libraries resolve from Maven and retain upstream licensing. The redistributed Gradle Wrapper's upstream license is in `src/android_stack_skills/data/licenses/Gradle-LICENSE.txt` and copied to generated projects. See [third-party notices](third-party.md).

## V1.1 UI 与图片库

以下矩阵适用于 Lightweight 和 Standard。构建基线为 JDK 17、SDK 36、minSdk 26、AGP 8.13.1、Gradle 8.14.3 和 Kotlin 2.2.20。验证任务为 `:app:assembleDebug :app:testDebugUnitTest`。

| UI | 图片库 | 选择规则与验证范围 |
|---|---|---|
| Compose | Coil 3.3.0 | 默认。继续使用 `coil-standard` 的 Compose AppImage API |
| Compose | Glide 4.16.0 | 显式 `--image glide`。使用 AndroidView 承载 ImageView |
| XML ViewBinding | Glide 4.16.0 | 默认。Activity 绑定 XML 并按生命周期收集共享 ViewModel 状态 |
| XML ViewBinding | Coil | 创建时拒绝。现有 `coil-standard` 的包装 API 需要 Compose |

Glide 版本以本次验证使用的 4.16.0 为准。XML 与 Compose 的 `debugRuntimeClasspath` 通过 `dependencyInsight` 检查。Views 封装使用 Glide RequestManager，Compose 桥接使用 `AndroidView` 的释放回调。 [Glide 4.16.0](https://github.com/bumptech/glide/releases/tag/v4.16.0) · [Glide 请求 API](https://bumptech.github.io/glide/doc/getting-started.html) · [AndroidView](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose) · [ViewBinding](https://developer.android.com/topic/libraries/view-binding)

两种预设共用 Repository、Network、Logging 和 ViewModel。Standard 在两个 UI 中均保留 Hilt。已有工程按选定模块的直接依赖与已安装记录保留图片库。IDE、真机及图片实际显示效果由开发者手动验收。

2026-11-03 实测结果如下。所有 Gradle 测试均为零失败、零跳过。

| 组合 | Lightweight | Standard |
|---|---:|---:|
| Compose + Coil | 构建通过，18 项测试 | 构建通过，18 项测试 |
| Compose + Glide | 构建通过，20 项测试 | 构建通过，20 项测试 |
| XML + Glide | 构建通过，20 项测试 | 构建通过，20 项测试 |
| XML + Coil | 创建前拒绝 | 创建前拒绝 |

Python 回归 53 项通过。V1 Android 回归矩阵完成 5 次构建和 1 项依赖冲突保护。Glide 的 JVM 用例验证占位图、失败图和空模型回退参数。CLI 重复安装返回 `already-installed`，文件哈希一致。对已使用 Glide 的 Compose 工程安装 Coil 返回退出码 2，工程文件哈希一致。

## V0.3.0 Retrofit on existing Kotlin projects

The Retrofit 0.1.1 sources and dependency pins were held constant. Commit `6761112` introduced Kotlin 2.2.20 as a shared Resolver baseline. The Recipe uses suspend calls, coroutines, OkHttp and Gson, and its source does not require a language feature introduced in Kotlin 2.2. Coroutines 1.10 adopted Kotlin 2.1.0, so compiler and dependency metadata compatibility required an actual build. [Coroutines 1.10 release notes](https://github.com/Kotlin/kotlinx.coroutines/releases/tag/1.10.0)

On 2026-11-03, independent Android projects passed `:app:assembleDebug :app:testDebugUnitTest` with the original Recipe. The POC also passed with Kotlin 2.0.21 targeting JVM 17. The CLI acceptance run covered the existing-project JVM 11 target and the JVM 17 baseline as follows.

| Kotlin | AGP | Gradle | Tested scope | Result |
|---|---|---|---|---|
| 2.0.21 | 8.13.1 | 8.14.3 | Plain Kotlin Android, JDK 17, JVM target 11, SDK 36, minSdk 24 | Debug APK, 14 tests passed |
| 2.2.20 | 8.13.1 | 8.14.3 | JDK 17, JVM target 17, SDK 36, minSdk 24 | Debug APK, 14 tests passed |

The Kotlin 2.0.21 profile is limited to Retrofit in a module without Compose or Hilt. The versions above are empirical results for this Recipe. The Kotlin documentation lists a narrower fully supported KGP 2.0.21 toolchain range. Release shrinking, device behavior, additional plugin combinations and other Kotlin, AGP or Gradle versions need separate evidence. [Kotlin Gradle plugin compatibility](https://kotlinlang.org/docs/gradle-configure-project.html)

Unverified Retrofit profiles block writes and recommend an isolated reproduction with the current versions. A documented requirement, such as AGP 8.13 requiring Gradle 8.13 or newer, yields a separate incompatible-version diagnostic. No toolchain edit is generated. [AGP 8.13 requirements](https://developer.android.com/build/releases/agp-8-13-0-release-notes)

Reproduce the CLI acceptance with JDK 17 and ANDROID_HOME configured.

```sh
.venv/bin/python scripts/verify_network_compatibility.py --output /tmp/network-compatibility-check
```

The script creates new fixtures, verifies that install without permission approval makes zero writes, previews and applies the explicitly authorized Manifest insertion, builds and tests both projects, checks toolchain file hashes, and confirms repeat install is a no-op. Existing test projects keep their original versions. The Python suite passed 63 tests. The existing V1 Android regression matrix passed five Gradle builds with 18 tests each and one conflict case with unchanged files.

`MyApplication` was inspected and planned read-only. Its Kotlin 2.0.21, AGP 8.13.1 and Gradle 8.14.3 matched the verified profile. The plan reported one blocker for the missing INTERNET declaration and supplied the exact source Manifest diff. Its complete app build remains a separate verification after permission approval.
