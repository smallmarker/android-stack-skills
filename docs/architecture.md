# Architecture

The Skill layer uses the open Agent Skills format. Hosts provide project file access and command execution. The CLI owns the workflow from inspection through validation and can also run directly.

The execution flow is **Skill → Inspector → Resolver → Plan → Installer → Validator**.

- Skill: routes intent to CLI, handles initialization in existing application code, interprets conflicts and actual build results.
- Recipe: YAML metadata, dependencies, original Kotlin templates, optional Hilt files, tests and provenance. JSON Schema restricts executable integration strategies.
- Inspector: reads literal module includes, Android plugin declarations, namespace, minSdk, Compose/Hilt, root plugins, catalog aliases, direct coordinates, Wrapper and source roots. It does not execute Gradle during planning. Unresolved versions remain `unknown`.
- Resolver: renders strict Jinja templates, computes Diff and dependency additions, checks versions, output paths and declarations. It blocks ambiguous dependency expressions, custom module mapping and existing image-loader configuration. No project mutations occur.
- Installer: checks planned before-images against disk, acquires an exclusive lock, writes a private persistent rollback journal, creates/updates files and stores source provenance, versions, environment and SHA-256 ownership records. Exceptions restore before-images. A crash leaves an explicit recover operation. Repeated installs verify owned source and required dependencies without mutating files.
- Validator: validates bundled schemas and installed ownership/dependencies, runs selected-module assembleDebug/testDebugUnitTest through the project's Wrapper, preserves combined stdout/stderr, and returns the real exit code. Success means the Gradle process succeeded, not that text was generated.

Shared build scripts are tracked as managed files with their latest tool-written hashes. Recipe source ownership is checked separately so a later Recipe's dependencies block does not make an earlier install non-idempotent. Status exposes changed managed files; a harmless manual build-script edit is not automatically reverted.

Project creation renders one shared Compose skeleton, adds Standard Hilt bindings when requested, then installs the same three Recipes. It writes a trusted upstream Wrapper JAR only after checking its pinned SHA-256, and pins the distribution hash. It never writes SDK locations or real credentials.

Planning intentionally understands a bounded Gradle subset. It is not a Kotlin/Groovy interpreter. Complex Gradle adaptation belongs to an agent reviewing the actual project and must be followed by a real build.

## Application architecture

[Architecture Foundation v1](architecture-foundation-v1.md) defines application decisions, shared contracts and verification. [Network Architecture v1](network-architecture-v1.md) is the first reference pattern. The [architecture audit](architecture-audit-v1.md) records current evidence, gaps and rollout.
