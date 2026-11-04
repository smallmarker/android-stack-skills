---
name: android-logging
description: Integrate Timber with a unified debug-only AppLogger and structured allowlisted fields in Kotlin Android projects. Use for Android logging setup, log initialization, release logging behavior, or Timber installation conflicts.
license: MIT
---

## CLI readiness

Before any Android operation, read [cli-requirements.json](cli-requirements.json) and [cli-setup.md](cli-setup.md). Check the trusted executable with `android-stack capabilities --json` and compare the protocol, capabilities and Recipe versions. Stop and ask for approval before preparing a missing or incompatible CLI. Use the same checked executable for the workflow.

Environment: Requires android-stack CLI, Python 3.11+, JDK 17, and Android SDK for actual builds.

Use `timber-standard` from Android Stack Skills. Fixed Kotlin implementations are bundled with the installed Python CLI; the skill folder does not need to carry another copy.

## Workflow

1. Locate the target project from the user/workspace. Use the CLI that passed the readiness check.
2. Run `android-stack inspect --project <path> --json`. For multiple Android modules select `--module :app` (or the actual module) in inspect/plan/install/verify. V1 safely installs only supported Kotlin DSL structures. Treat unknown values as unknown.
3. Run `android-stack status --project <path>` for existing Recipe state. For status-only requests, report the result without installing anything.
4. Run `android-stack plan --project <path> --recipe timber-standard`. Review dependency versions, file Diff, namespace, DI and conflicts. Planning does not write files. Do not silently upgrade existing versions or replace user source. Stop deterministic installation if the plan has conflicts; explain the concrete conflict. If the requested integration authorizes a narrow manual adaptation, preserve existing architecture and review its Diff.
5. Run `android-stack install --project <path> --recipe timber-standard` once the plan is safe; this reports installed-unverified until initialization and the final build succeed. A repeated installation must return already-installed without changing files. The installer records hashes in `.android-stack/manifest.json`.
6. Call AppLogger.initialize(BuildConfig.DEBUG) from the existing Application without replacing it. d/i/w/e accept developer-authored static messages only. Use typed LogField values or Redacted for dynamic information. No arbitrary-string sanitizer is promised. Release facade calls are silent; preserve existing Timber trees.
7. Run `android-stack verify --project <path>` after initialization/adaptation. Verification runs real assembleDebug and testDebugUnitTest tasks. Nonzero exit or a failed log is a failure, even if installation wrote files. Report the exact commands and log location. Do not claim success from generated text alone.
8. For interrupted writes inspect `.android-stack/journal.json`; `android-stack recover --project <path>` restores recorded changes only if no subsequent user edits would be overwritten. Do not delete a lock held by another process. Gradle failures leave generated source and logs for diagnosis; they do not call for blindly rolling back user changes.

## Example

“给当前项目集成统一日志” → inspect → plan `timber-standard` → install → initialize using generated `app/android-stack/logging/Usage.md` → verify. Report conflicts and unresolved environment failures accurately.
