# Contributing

Use Python 3.11+ and `pip install -e '.[test]'`. Run `pytest -q` before proposing changes.

Canonical Recipe sources live in `recipes/`. Copy changes into `src/android_stack_skills/data/recipes/` for packaging; the distribution test enforces byte equality. Skills in `skills/` must also be copied to `src/android_stack_skills/data/skills/`; the distribution test enforces their equality. Shared project skeletons live in `src/android_stack_skills/data/project-templates/`. `python scripts/refresh_examples.py` regenerates examples while retaining ignored build caches. It is a maintainer operation and intentionally replaces generated example files.

Each Recipe needs a valid Schema manifest, upstream version/license provenance, actual Kotlin tests and idempotent/conflict tests. Run the Android matrix from docs/testing.md before marking an Android-facing change verified. Do not relax or remove failing tests to pass CI.

Keep changes narrow. Avoid arbitrary Gradle rewriting or silent dependency upgrades. Explain unsupported structures as actionable conflicts. Never embed local SDK paths, secrets or real tokens. Update docs/compatibility.md and docs/progress.md with observed results, including failures.

Suggested commits follow phases: chore/init, feat/engine, feat/recipe, feat/generator, feat/skills, test/verification, docs/delivery. Remote pushes and releases require separate user authorization.

For cross-agent compatibility reports, follow the evidence checklist in [Agent compatibility](docs/agent-compatibility.md). Keep host-specific installation instructions in the docs and use the same Skill instructions across hosts.
