# Android Stack Skills

[简体中文](README.md)

Agent-agnostic Android development skills powered by verified integration recipes.

Scaffold Kotlin Android projects, integrate libraries into existing apps, and run Gradle verification from natural-language requests. The Skills follow the open [Agent Skills specification](https://agentskills.io/specification) and require a host that can access local project files and run commands.

## Why Android Stack Skills

The agent interprets the request, Recipes supply verified implementations, and the CLI applies and verifies changes deterministically. Fixed implementations and dependency versions make results reproducible, and the plan lets you review changes and conflicts before applying them.

## Quick Start

Install the Skills and CLI separately for agent use. For direct command-line use, install the CLI alone.

### 1. Install Agent Skills

Requires Node.js and npm. Run this in the target project directory and select your coding agent.

```sh
npx skills add smallmarker/android-stack-skills
```

### 2. Install Android Stack CLI

Requires Python 3.11+ and pipx. After installation, run the checks below from the environment the agent uses to execute commands. If the CLI is missing, run `pipx ensurepath` and restart the host.

```sh
pipx install git+https://github.com/smallmarker/android-stack-skills.git@v0.2.0
android-stack version
android-stack recipes list
```

### 3. Start using the Skills

Send the request below to your agent. Builds require JDK 17, Android SDK Platform 36 / Build Tools 35.0.0, and access to Gradle and Maven dependencies.

> Use Android Stack Skills to create a Kotlin Android project with XML + ViewBinding, Standard MVVM, Glide, Retrofit, Timber, and Hilt, then run Gradle build verification.

## Features & Supported Stacks

- **Lightweight** uses single-module Kotlin + MVVM with direct repository construction.
- **Standard** adds Hilt and a repository interface with its implementation.
- Both presets integrate Retrofit + OkHttp, Timber, and the selected image library, and share ViewModel and StateFlow.

| UI | Image loading |
|---|---|
| Compose | Coil (default) |
| XML + ViewBinding | Glide (default) |
| Compose | Glide (explicit selection via AndroidView) |
| XML + ViewBinding | The current Coil Recipe provides a Compose API only |

The XML + Coil limitation comes from this project’s `coil-standard` Recipe. Coil itself also supports Android Views.

## Create a Project

```sh
android-stack create --name StandardDemo --package com.example.standard --preset standard --ui xml --output ./StandardDemo
```

Compose is the default UI. To use Glide with Compose, pass `--ui compose --image glide`. Creation runs `assembleDebug` and `testDebugUnitTest` by default and preserves the project and logs if verification fails. Use `--skip-verify` to generate an unverified project. Existing output directories are protected.

Open the [Lightweight example](examples/lightweight-app) or [Standard example](examples/standard-app) in Android Studio.

## Integrate Existing Projects

```sh
android-stack inspect --project ./MyApp --json
android-stack plan --project ./MyApp --recipe retrofit-standard
android-stack install --project ./MyApp --recipe retrofit-standard --verify
```

Use the same workflow with `coil-standard`, `glide-standard`, and `timber-standard`. In multi-module projects, select the target module with `--module :app`. Check `image_libraries` in the inspection output to choose a Recipe for the existing library, then follow the generated `app/android-stack/*/Usage.md` for initialization.

Planning is read-only. The CLI reuses matching dependency versions and stops on dependency or source conflicts. Repeated installs verify existing content and leave files intact. Existing projects require Kotlin DSL and a literal namespace and minSdk. The Network and Image Recipes require INTERNET permission.

## Supported Coding Agents

Codex has been verified for installation, natural-language triggers, CLI calls, and Android builds. Installer file placement has been verified for Claude Code, Cursor, OpenCode, and GitHub Copilot. Their full workflows are pending verification. See the [agent compatibility matrix](docs/agent-compatibility.md).

```sh
npx skills add smallmarker/android-stack-skills --agent codex
npx skills add smallmarker/android-stack-skills --agent claude-code
npx skills add smallmarker/android-stack-skills --agent cursor
npx skills add smallmarker/android-stack-skills --agent opencode
npx skills add smallmarker/android-stack-skills --agent github-copilot
```

Installation defaults to the current project. Add `--global` for user-level installation, or use `--skill` to select a single Skill.

```sh
npx skills add smallmarker/android-stack-skills --skill android-project
npx skills list --agent codex
```

Add `--global` to the `list` command to inspect user-level installations. Reopen the target project and ask your agent to find `android-project` to confirm host discovery.

## Advanced Installation

### Manual Installation (Advanced)

Copy each complete Skill directory from the repository’s `skills/` folder to the location documented by your host. For example, Codex can use `.agents/skills/` in the project or `~/.agents/skills/` at user scope. Follow your host’s discovery paths and review existing directories with the same names before copying.

If you installed from a wheel, locate the bundled Skills using the Python environment that contains the CLI.

```sh
python -c 'from importlib.resources import files; print(files("android_stack_skills").joinpath("data", "skills"))'
```

## Compatibility & Limitations

The tested baseline is AGP 8.13.1, Gradle 8.14.3, Kotlin 2.2.20, and Compose BOM 2025.08.01 on macOS arm64 with JDK 17. Generated apps support Android API 26+. Manual checks of Android Studio, devices, and image rendering for XML / Glide are pending.

Automatic integration excludes Groovy writes, AGP 9 built-in Kotlin, dynamic dependencies and bundles, custom projectDir / includeBuild, complex convention plugins, multiplatform migration, and automatic merging of existing ImageLoader setups. See the [testing guide](docs/testing.md) for build logs and recovery guidance.

Build logs are saved to `.android-stack/verification.log`. After an interrupted install, confirm no other process holds the installer lock, then run `android-stack recover --project ./MyApp`. Recovery protects edits made after the interruption.

The Early Preview source is public on GitHub under `main` and the [`v0.2.0` tag](https://github.com/smallmarker/android-stack-skills/tree/v0.2.0). Install from Git. GitHub Releases and PyPI packages are pending.

## Documentation & Contributing

[Architecture](docs/architecture.md) · [Android compatibility](docs/compatibility.md) · [Recipe spec](docs/recipe-spec.md) · [Testing](docs/testing.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](docs/roadmap.md)

[android-project](skills/android-project/SKILL.md) · [android-network](skills/android-network/SKILL.md) · [android-image](skills/android-image/SKILL.md) · [android-logging](skills/android-logging/SKILL.md)
