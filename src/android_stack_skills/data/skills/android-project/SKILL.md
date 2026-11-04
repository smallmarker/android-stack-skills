---
name: android-project
description: Create a Kotlin Android Compose or XML ViewBinding MVVM project with Retrofit, Coil or Glide, and Timber using Android Stack Skills. Use for new Android apps, Lightweight scaffolding, or a Standard project with Hilt. Does not migrate an existing application's architecture.
license: MIT
---

## CLI readiness

Before any Android operation, read [cli-requirements.json](cli-requirements.json) and [cli-setup.md](cli-setup.md). Check the trusted executable with `android-stack capabilities --json` and compare the protocol, capabilities and Recipe versions. Stop and ask for approval before preparing a missing or incompatible CLI. Use the same checked executable for the workflow.

Environment: Requires android-stack CLI, Python 3.11+, JDK 17, Android SDK 36, and Maven/Gradle access.

## Choose the preset

Use lightweight for a small single-module app with explicit constructors. Use standard when Hilt and repository interface/implementation separation are requested. Both reuse retrofit-standard and timber-standard. Pass --ui xml for XML ViewBinding. Compose defaults to Coil and XML defaults to Glide. Use --image glide when explicitly requested for Compose through AndroidView. XML + Coil is rejected by create.

## Create and verify

1. Establish project name, dotted package name, and output directory from the request. Infer routine choices. Never overwrite an existing directory or change unrelated repositories.
2. Check Java 17 and Android SDK using the CLI environment that passed readiness.
3. Run `android-stack create --name DemoApp --package com.example.demo --preset standard --output ./DemoApp` with the requested values. The default runs actual Gradle builds and unit tests. The bundled wrapper and distribution are SHA-256 pinned.
4. `--skip-verify` is only for deliberate offline generation; clearly report unverified output. Do not call generated code tested in that mode.
5. Run `android-stack inspect --project ./DemoApp` and `android-stack status --project ./DemoApp`. Check all three recipes are recorded. Follow generated README and app/android-stack/*/Usage.md for APIs. No real backend or credentials are invented.
6. A build failure preserves generated source and `.android-stack/verification.log`. Diagnose the first error and rerun `android-stack verify --project ./DemoApp`. Generation failures clean only the newly created output; existing directories are protected. Report remaining failures without presenting them as success.

## Example

“创建一个叫 DemoApp 的 Compose + MVVM 项目，使用 Hilt” selects standard. The deliverable is the generated directory, build/test results, and API initialization guidance. Do not push or publish without explicit user authorization.
