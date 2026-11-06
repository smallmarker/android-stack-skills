---
name: android-network
description: Integrate Retrofit and OkHttp into an existing Kotlin Android project using typed results, coroutine-safe error mapping, and token headers. Use for networking setup, adding or reviewing business APIs in an existing stack, checking Recipe status, and Retrofit version conflicts.
license: MIT
---

## CLI readiness

Before using the CLI to inspect, install or verify a Recipe, read [cli-requirements.json](cli-requirements.json) and [cli-setup.md](cli-setup.md). Check the trusted executable with `android-stack capabilities --json` and compare the protocol, capabilities and Recipe versions. Stop and ask for approval before preparing a missing or incompatible CLI. Use the same checked executable for the workflow.

The optional gate beside this Skill can perform the check. Run `python3 <skill-directory>/scripts/cli_gate.py` or pass `--cli /absolute/path/to/android-stack`. To forward a command, append `--` and the CLI arguments. The gate never prepares an environment. Confirm permission for any reviewed Manifest edit separately from CLI preparation.

Environment: Requires android-stack CLI, Python 3.11+, JDK 17, and Android SDK for actual builds.

Use `retrofit-standard` from Android Stack Skills. Fixed Kotlin implementations are bundled with the installed Python CLI; the skill folder does not need to carry another copy.

## Extend an existing network stack

For a business API request, start here. Existing source and Gradle are sufficient for ordinary incremental development. Apply the CLI readiness gate if the task requires CLI operations.

1. Locate the target module and read its architecture decision or README, the existing Service, DTOs, results, Repository and DI, plus the installed `android-stack/network/Usage.md` when present. Identify Recipe-owned files from the installation record and leave them intact. Preserve the project's existing network stack and conventions.
2. Confirm the method, route, exact HTTPS trust origin, authentication owner, redirect policy, side effects, retry permission, any server idempotency-key contract, sensitive headers, success-body and error contract. Reuse the existing Retrofit/OkHttp instance and result model. Define required wire fields based on the endpoint. Preserve the difference between malformed JSON, missing body, invalid fields, HTTP failures and transport errors.
3. In application-owned source, declare the endpoint on an application-owned Service. Use `Response<Dto>` for explicit body semantics. With Recipe 0.2.0 or later reuse `safeApiResponse` for a required payload or `safeEmptyApiResponse` with `Response<Unit>` for an empty-success contract. Validate before mapping to an application model. Respect the existing coroutine scope and let cancellation propagate.
4. With Recipe 0.3.0, use a factory instance per exact scheme/host/port. A third-party client has its own config and no application TokenProvider or credential headers. The factory rejects foreign destinations, strips per-request auth/cookies, disables redirects/authenticators and marks non-GET/HEAD bodies one-shot. A bodyless DELETE becomes a zero-length body. GET/HEAD must have read semantics. Cookie auth and builder/interceptor changes need a reviewed adaptation. Keep HTTP content, URLs and credentials out of logs.
5. Add tests that use the actual converter and assert the mapped model, HTTP failure and invalid responses, including missing required fields. If changing request lifetime, test in-flight cancellation. For auth/URL changes, use two HTTPS services and the production factory with test-only certificate trust; assert received headers and target counts. For writes, assert method/path/body/count for success, 401, 408, 503, redirects, timeout, disconnect and cancellation. Client replay controls cannot prove server exactly-once execution; application retries require an explicit server contract. Run the target module's Gradle assembleDebug and testDebugUnitTest, then report the real results.
6. Keep unrelated source and the toolchain intact. A request like “新增获取订单详情的 API” uses this workflow with the order contract, the existing client and application-owned tests. If an older install lacks the new helpers, adapt at the existing app-owned data boundary. A Recipe upgrade is a separate reviewed change.

## Install or inspect a Recipe

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
