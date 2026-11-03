# Android Stack Skills

Production-ready Android stacks, powered by Agent Skills.

A deterministic Android integration toolkit: agents interpret requests, Recipes provide fixed Kotlin implementations, and the CLI inspects, plans, installs and validates changes. Repeated installations preserve files; conflicts stop automatic changes. See [delivery evidence and open items](docs/delivery.md).

## Install

**Early Preview 0.2.0**. Using this toolkit from Codex requires two separate installations, the Agent Skills and the Python CLI.

The CLI requires Python 3.11+. Android builds require JDK 17, Android SDK Platform 36 / Build Tools 35.0.0 and Maven / Gradle access.

### Agent Skills (Codex)

Run the following from the intended project root to install all four Skills for the current Codex project. Add `--skill android-project` to install only the project scaffolding Skill.

```sh
npx skills add smallmarker/android-stack-skills --agent codex
```

### Python CLI

```sh
pipx install git+https://github.com/smallmarker/android-stack-skills.git@v0.2.0
android-stack --help
android-stack version
android-stack recipes list
```

You can also install the locally built wheel in a dedicated virtual environment. `android_stack_skills-0.2.0-py3-none-any.whl`

If Codex cannot find the Skills, check that they were installed for the intended project and reopen the session. If `android-stack` is missing, run `pipx ensurepath` and restart the terminal that launches Codex. For dependency conflicts, inspect the output of `android-stack plan`.

## Create

```sh
export ANDROID_HOME=/path/to/android/sdk
android-stack create --name DemoApp --package com.example.demo --preset lightweight --output ./DemoApp
android-stack create --name StandardDemo --package com.example.standard --preset standard --ui xml --output ./StandardDemo
android-stack create --name GlideCompose --package com.example.glidecompose --ui compose --image glide --output ./GlideCompose
```

Compose is the default UI. When `--image` is omitted, Compose uses Coil and XML uses Glide. Compose + Glide uses an ImageView through AndroidView. XML + Coil is rejected before output creation because the current Coil Recipe provides a Compose API.

Both UIs share MVVM, StateFlow, Repository, Network and Logging. The XML Activity uses ViewBinding and collects state while started. Standard adds Hilt and a repository interface with its implementation.

Creation runs real Gradle build/tests by default. `--skip-verify` explicitly generates unverified output. Existing output directories are protected. Generation errors clean newly created output; build failures preserve the project and full logs.

## Integrate existing projects

```sh
android-stack inspect --project ./MyApp --json
android-stack plan --project ./MyApp --recipe retrofit-standard
android-stack install --project ./MyApp --recipe retrofit-standard --verify
android-stack install --project ./MyApp --recipe coil-standard --verify
android-stack install --project ./MyApp --recipe timber-standard --verify
android-stack status --project ./MyApp
android-stack verify --project ./MyApp
```

Use `--module :app` for multiple Android modules. `plan` and `install --dry-run` are read-only. `--json` emits structured reports. Installation without `--verify` reports **installed-unverified**. Matching dependency versions are reused; different/unknown versions, existing generated files or conflicting Kotlin declarations block installation.

Existing projects require Kotlin DSL, a literal namespace/minSdk, and INTERNET permission for network/images. Coil requires explicitly enabled Compose. The installer appends a bounded dependencies block instead of rewriting arbitrary Gradle programs. It preserves Application code: follow the generated `app/android-stack/*/Usage.md` for initialization.

```kotlin
val api = HttpClientFactory.retrofit(NetworkConfig("https://api.example.com/"))
    .create(UserApi::class.java)
val result = UserRepository(api).getUser() // inside a coroutine
// Application.onCreate:
AppImages.initialize(this)
AppLogger.initialize(BuildConfig.DEBUG)
// Compose:
AppImage(url = avatarUrl, shape = CircleShape, contentDescription = "User avatar")
AppLogger.d("Home", "Page created")
```

Hilt integrations require application bindings for NetworkConfig and TokenProvider; Standard includes examples. Network cancellation propagates, errors expose no response bodies or credentials, and production clients require HTTPS. AppImage provides shared caching, shape/scaling, Painter placeholders/errors and loading/failure slots. Logger release calls are silent. Free text is for static developer messages; dynamic fields use a typed allowlist. Arbitrary-text sanitization is not promised.

For existing projects, check the selected module's `image_libraries` in `inspect`. Keep the existing library and version. Plans block an alternative image library or a version conflict. Use `android-stack plan --project ./MyApp --recipe glide-standard` and then `android-stack install --project ./MyApp --recipe glide-standard --verify` to install Glide. Use `binding.preview.loadGlide(url)` from a ViewBinding Activity, or use the same extension on an AndroidView ImageView. See the [compatibility matrix](docs/compatibility.md#v11-ui-与图片库).

## Agent Skills

For wheel-only installations, locate bundled Skills with `python -c 'from importlib.resources import files; print(files("android_stack_skills").joinpath("data", "skills"))'`.

Install the CLI first, then copy the four folders from `skills/` to `<project>/.agents/skills/` or `~/.agents/skills/`. Inspect any existing same-named folders before copying. Codex paths were checked against [official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills) on 2026-11-02; other agents have their own discovery paths. Restart the host if discovery does not update.

- [android-project](skills/android-project/SKILL.md): new Compose or XML/MVVM applications.
- [android-network](skills/android-network/SKILL.md): Retrofit/OkHttp, status and conflicts.
- [android-image](skills/android-image/SKILL.md): Coil/AppImage and Glide/ImageView.
- [android-logging](skills/android-logging/SKILL.md): Timber/AppLogger.

Example requests: “Create a Standard Android project”, “Install Retrofit”, “Add Coil image loading”, “Set up logging”, “Check installed networking”, “Install again”, “Resolve an existing Retrofit version conflict”. Frontmatter and isolated Codex session results are recorded in the [RC report](docs/delivery.md); other Agent hosts are not certified.

## Compatibility and recovery

Tested baseline: AGP 8.13.1, Gradle 8.14.3, Kotlin 2.2.20, Compose BOM 2025.08.01, macOS arm64 and JDK 17. See [pinned versions and latest-version audit](docs/compatibility.md).

V1 excludes Groovy writes, AGP 9 built-in Kotlin, dynamic dependencies/bundles, custom projectDir/includeBuild, complex convention plugins, multiplatform migration and automatic merging of existing ImageLoader setups. No remote repository or release has been published.

Interrupted writes leave `.android-stack/journal.json`. After confirming no other process is active, `android-stack recover --project ./MyApp` restores recorded files while protecting subsequent edits. Build logs remain in `.android-stack/verification.log`. No failed compilation is reported as successful integration.

[Architecture](docs/architecture.md) · [Recipe spec](docs/recipe-spec.md) · [Testing](docs/testing.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](docs/roadmap.md) · [中文](README.md)
