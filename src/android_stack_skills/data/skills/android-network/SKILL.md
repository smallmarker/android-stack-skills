---
name: android-network
description: Integrate Retrofit and OkHttp into an existing Kotlin Android project using typed results, coroutine-safe error mapping, and token headers. Use for networking setup, API client installation, checking networking Recipe status, repeated installation, and Retrofit version conflicts.
license: MIT
---

## CLI readiness

Before any Android operation, read [cli-requirements.json](cli-requirements.json) and [cli-setup.md](cli-setup.md). Check the trusted executable with `android-stack capabilities --json` and compare the protocol, capabilities and Recipe versions. Stop and ask for approval before preparing a missing or incompatible CLI. Use the same checked executable for the workflow.

The optional gate beside this Skill can perform the check. Run `python3 <skill-directory>/scripts/cli_gate.py` or pass `--cli /absolute/path/to/android-stack`. To forward a command, append `--` and the CLI arguments. The gate never prepares an environment. Confirm permission for any reviewed Manifest edit separately from CLI preparation.

Environment: Requires android-stack CLI, Python 3.11+, JDK 17, and Android SDK for actual builds.

Use `retrofit-standard` from Android Stack Skills. Fixed Kotlin implementations are bundled with the installed Python CLI; the skill folder does not need to carry another copy.

## Workflow

1. Locate the target project from the user/workspace. Use the CLI that passed the readiness check.
2. Run `android-stack inspect --project <path> --json`. For multiple Android modules select `--module :app` (or the actual module) in inspect/plan/install/verify. V1 safely installs only supported Kotlin DSL structures. Treat unknown values as unknown.
3. Run `android-stack status --project <path>` for existing Recipe state. For status-only requests, report the result without installing anything.
4. Run `android-stack plan --project <path> --recipe retrofit-standard --json`. Read `diagnostics` for the category, cause, safe action and any patch. Preserve the project's Kotlin, AGP, Gradle and existing dependencies. The tested Kotlin 2.0.21 profile uses AGP 8.13.1, Gradle 8.14.3 and a plain Kotlin Android module. Keep Compose and Hilt on their separately verified baseline. For an unverified combination, inspect the Recipe's pinned dependencies and compiler evidence, then validate the exact versions in an isolated project. A baseline gate or an upstream support range alone does not establish a compiler failure.
5. Handle missing INTERNET separately. Present the diagnostic's Manifest path and diff and ask for explicit permission to add that declaration. After approval, rerun the plan with `--add-internet-permission` and use the same flag on install only if the approved edit is still the one shown and all other blockers are resolved. A manually approved edit is also valid. If a Manifest is malformed or has a merge override, review it manually and confirm the merged permission. A blocked plan does not authorize any write.
6. Install with `android-stack install --project <path> --recipe retrofit-standard` when clear of blockers. Stop on an incompatible toolchain, existing dependency mismatch or source conflict. Preserve existing files and propose a tested alternative or isolated reproduction. For any proposed Kotlin, AGP or Gradle upgrade, show old/new versions, affected build files, plugin and SDK impacts, CI implications and a rollback path. Obtain explicit user approval before changing versions. Keep the Installer checks active. A second install should report already-installed. Use the generated Usage.md for optional Hilt bindings and application-owned endpoint configuration.
7. Run `android-stack verify --project <path>` after initialization/adaptation. Verification runs real assembleDebug and testDebugUnitTest tasks. Nonzero exit or a failed log is a failure, even if installation wrote files. Report the exact commands and log location. Do not claim success from generated text alone.
8. For interrupted writes inspect `.android-stack/journal.json`; `android-stack recover --project <path>` restores recorded changes only if no subsequent user edits would be overwritten. Do not delete a lock held by another process. Gradle failures leave generated source and logs for diagnosis; they do not call for blindly rolling back user changes.

## Example

“给当前项目集成Retrofit” → inspect → plan `retrofit-standard` → install → initialize using generated `app/android-stack/network/Usage.md` → verify. Report conflicts and unresolved environment failures accurately.
