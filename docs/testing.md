# Testing

Current RC results were observed on 2026-11-03: 38 Python tests, four isolated Codex sessions, independent Notes integration and wheel-only preset builds passed. See delivery.md for the authoritative four-category report. Earlier 2026-11-02 evidence below is historical. Full acceptance reports are in [validation/](validation/) and the status summary is in [delivery.md](delivery.md).

## Python

```sh
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

Coverage includes safe YAML/strict JSON Schema, unknown values, Kotlin/Groovy inspection, catalog dependencies, matching/conflicting versions, deterministic plans, strict templates, file/declaration conflicts, path traversal/symlinks, concurrency checks, rollback/recovery, repeated installation, installed-dependency drift, CLI subprocess output/exit codes, wrapper checksum and two presets. The runner failure test executes a deliberately failing local shell fixture; it is not claimed as an Android build.

## Real Android acceptance matrix

```sh
export ANDROID_HOME=/path/to/android/sdk
python scripts/verify_android.py --output /tmp/android-stack-acceptance-new
```

The output directory must not already exist. The script retains every test project and its complete Gradle log. It copies generated examples to create controlled existing-project fixtures, removes only the tested Recipe's files/record while retaining existing matching dependencies, reinstalls, checks byte-for-byte idempotency, then runs real Gradle assembleDebug/testDebugUnitTest.

Cases: clean Kotlin/Compose, existing Retrofit, existing Coil, existing Timber, existing Hilt, incompatible Retrofit 2.9.0. Five compile/build/test successfully; each has 13 executed tests. The sixth must reject installation and preserve the project. It is not counted as a successful Android compilation.

For generated projects:

```sh
android-stack verify --project examples/lightweight-app
android-stack verify --project examples/standard-app
# Equivalent direct build:
cd examples/standard-app
./gradlew :app:assembleDebug :app:testDebugUnitTest --console=plain --stacktrace
```

The original nine network test methods (the current Recipe adds five RC regressions) cover success, HTTP 400/401/500, read timeout, refused connection, invalid JSON, nonempty/empty/null tokens, cancellation, unexpected programming errors and HTTPS/credential config. Tests share one HTTP-error loop and one token loop, so scenario count exceeds JUnit method count. Additional tests cover home Repository, release logger silence, typed redaction and debug exception-detail suppression.

Test-machine proxy was passed with GRADLE_OPTS system properties, not persisted in generated projects. If Maven stalls, diagnose your actual proxy/firewall and pass appropriate JVM flags. Do not copy this machine's proxy values as a universal configuration.

## Skills

Each SKILL.md passed the bundled skill-creator quick_validate.py. Natural-language acceptance cases are in [skill-scenarios.md](skill-scenarios.md). All four fresh Codex CLI sessions selected and read the matching Skill from wheel resources, invoked the installed CLI and completed actual Gradle verification. Claude and other hosts were not tested. See delivery.md and skill-scenarios.md for precise evidence and reproduction.

## Packaging

```sh
python -m pip install build
python -m build --wheel
pip install --target /tmp/android-stack-wheel-install --no-deps dist/*.whl
# Run outside the source checkout, with PYTHONPATH pointing to that target.
```

Check that hidden .gitignore templates, all five Recipe manifests, JSON Schema, Kotlin templates, Gradle JAR and license are present. Recipe copies under recipes/ and Python package data must match exactly. The generator checks Wrapper SHA-256 before writing any output.

## Manual runtime verification still required

Open each generated example in Android Studio, deploy to an API 26+ emulator/device, confirm the local home screen, run an AppImage with real placeholder/error assets, and wire a controlled HTTPS backend before live API checks. These GUI/device tasks are explicitly excluded from Codex RC acceptance and do not block its automated result. No device/emulator UI or live remote-service verification is claimed by the build tests. Windows wrapper and Linux execution are not certified by the macOS build run.
