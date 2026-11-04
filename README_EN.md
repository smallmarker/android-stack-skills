# Android Stack Skills

[简体中文](README.md)

Agent-agnostic Android development skills powered by verified integration recipes.

Scaffold Kotlin Android projects, integrate libraries into existing apps, and run Gradle verification from natural-language requests. The Skills follow the open [Agent Skills specification](https://agentskills.io/specification) and require a host that can access local project files and run commands.

## Why Android Stack Skills

The agent interprets the request, Recipes supply verified implementations, and the CLI applies and verifies changes deterministically. Fixed implementations and dependency versions make results reproducible, and the plan lets you review changes and conflicts before applying them.

## Quick Start

**Installing a Skill adds only its files.** The agent checks or prepares the Python CLI when you request a Recipe operation.

### 1. Install with an AI Agent

Send this prompt to Codex in the target project. Choose one, several, or all Skills and specify project or user scope.

> Help me install the Skills from https://github.com/smallmarker/android-stack-skills. First list all Skills and what they do so I can choose. Wait for my selection and scope, then install only those Skill files. Preserve any modified copies and leave Python CLI setup for later.

### 2. Install a Specific Skill

Copy the prompt for the Skill you want. The SkillsMP prompt defaults to project scope. Explicitly request user scope if you want it.

**android-project**

> Follow https://skillsmp.com/skill-install/prompt.md to install only the Agent Skill at https://github.com/smallmarker/android-stack-skills/tree/main/skills/android-project.

**android-network**

> Follow https://skillsmp.com/skill-install/prompt.md to install only the Agent Skill at https://github.com/smallmarker/android-stack-skills/tree/main/skills/android-network.

**android-image**

> Follow https://skillsmp.com/skill-install/prompt.md to install only the Agent Skill at https://github.com/smallmarker/android-stack-skills/tree/main/skills/android-image.

**android-logging**

> Follow https://skillsmp.com/skill-install/prompt.md to install only the Agent Skill at https://github.com/smallmarker/android-stack-skills/tree/main/skills/android-logging.

### 3. Install with npx

Run from the target project with Node.js and npm.

```sh
npx skills add smallmarker/android-stack-skills
```

An interactive terminal can prompt for Skills and target agents. Some agent environments install all Skills automatically. To explicitly choose Codex and one Skill, use:

```sh
npx skills add smallmarker/android-stack-skills --agent codex --skill android-network
```

Add `--global` for a user-scoped installation. Check same-named directories before repeating an installation because npx can replace local edits. Codex uses `.agents/skills/` for project scope and `~/.agents/skills/` for user scope. Open a fresh session to check discovery. See the [Prompt installation results](docs/skill-installation.md).

### 4. Start Using

> Integrate Retrofit + OkHttp into this project while preserving its Kotlin, AGP, Gradle, and source directory layout.

When you request a Recipe operation, the agent checks a trusted CLI with `android-stack capabilities --json`. If a compatible CLI is missing, the agent presents the pinned GitHub commit, isolated environment path, and installation effects, then asks for approval before installing. Android builds require JDK 17, Android SDK Platform 36 / Build Tools 35.0.0, and access to Gradle and Maven dependencies. [CLI setup guide](skills/android-network/cli-setup.md)

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

Planning is read-only. The CLI reuses matching dependency versions and stops on dependency or source conflicts. Repeated installs verify existing content and leave files intact. Existing projects require Kotlin DSL and a literal namespace and minSdk. The Network and Image Recipes require INTERNET permission. If it is missing, review the proposed manifest edit with `plan --add-internet-permission` and pass `--add-internet-permission` to `install` only after explicit approval.

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
