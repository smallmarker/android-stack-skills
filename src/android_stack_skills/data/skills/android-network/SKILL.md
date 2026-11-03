---
name: android-network
description: Integrate Retrofit and OkHttp into an existing Kotlin Android project using typed results, coroutine-safe error mapping, and token headers. Use for networking setup, API client installation, checking networking Recipe status, repeated installation, and Retrofit version conflicts.
license: MIT
---

Environment: Requires android-stack CLI, Python 3.11+, JDK 17, and Android SDK for actual builds.

Use `retrofit-standard` from Android Stack Skills. Fixed Kotlin implementations are bundled with the installed Python CLI; the skill folder does not need to carry another copy.

## Workflow

1. Locate the target project from the user/workspace. Run `android-stack version` and `android-stack recipes list`. If the CLI is unavailable, ask the user to install Android Stack CLI using the official repository README and ensure `android-stack` is on the agent process PATH before continuing.
2. Run `android-stack inspect --project <path> --json`. For multiple Android modules select `--module :app` (or the actual module) in inspect/plan/install/verify. V1 safely installs only supported Kotlin DSL structures. Treat unknown values as unknown.
3. Run `android-stack status --project <path>` for existing Recipe state. For status-only requests, report the result without installing anything.
4. Run `android-stack plan --project <path> --recipe retrofit-standard`. Review dependency versions, file Diff, namespace, DI and conflicts. Planning does not write files. Do not silently upgrade existing versions or replace user source. Stop deterministic installation if the plan has conflicts; explain the concrete conflict. If the requested integration authorizes a narrow manual adaptation, preserve existing architecture and review its Diff.
5. Run `android-stack install --project <path> --recipe retrofit-standard` once the plan is safe; this reports installed-unverified until initialization and the final build succeed. A repeated installation must return already-installed without changing files. The installer records hashes in `.android-stack/manifest.json`.
6. Require INTERNET permission. Ask for the real base URL only when wiring live usage; installation embeds no credentials or endpoint. Never log tokens. Hilt projects must supply NetworkConfig and TokenProvider bindings; use the generated Usage.md. CancellationException must propagate. No universal response envelope or automatic token refresh is assumed.
7. Run `android-stack verify --project <path>` after initialization/adaptation. Verification runs real assembleDebug and testDebugUnitTest tasks. Nonzero exit or a failed log is a failure, even if installation wrote files. Report the exact commands and log location. Do not claim success from generated text alone.
8. For interrupted writes inspect `.android-stack/journal.json`; `android-stack recover --project <path>` restores recorded changes only if no subsequent user edits would be overwritten. Do not delete a lock held by another process. Gradle failures leave generated source and logs for diagnosis; they do not call for blindly rolling back user changes.

## Example

“给当前项目集成Retrofit” → inspect → plan `retrofit-standard` → install → initialize using generated `app/android-stack/network/Usage.md` → verify. Report conflicts and unresolved environment failures accurately.
