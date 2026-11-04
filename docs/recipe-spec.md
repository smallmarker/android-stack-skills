# Recipe protocol v1

The executable schema is [`recipe.schema.json`](../src/android_stack_skills/data/recipe.schema.json), JSON Schema Draft 2020-12, validated with jsonschema. Unknown top-level fields are rejected. YAML uses safe_load. Invalid types, configurations, versions, missing templates and unsafe paths report an actionable StackError.

| Field | Contract |
|---|---|
| id | lowercase identifier, globally unique |
| name / description | nonempty strings |
| version | three numeric SemVer components |
| category | project / network / image / logging |
| source | HTTPS repository, revision tag/version, license, copied_source list |
| requirements | language=kotlin, gradle_dsl=kotlin, min_sdk >=21, optional compose boolean |
| dependencies | module=`group:artifact`, pinned numeric version, implementation or testImplementation |
| features | list of supported capabilities |
| variables | documented variable names and descriptions |
| files | template path, rendered output path, optional when=hilt |
| integration | append-dependency-block or create-new-directory, optional idempotency/reuse metadata |
| validation | schema, owned-file-hashes, gradle-build, unit-test |

See [the network Recipe](../recipes/network/retrofit-standard/recipe.yaml) for a complete runnable example.

Integration variables are `package`, `package_path`, `module`, `hilt`; they come from inspection, never arbitrary user template execution. Project presets add `name` and use the shared skeleton under data/project-templates, their README template, and listed reused Recipes. StrictUndefined catches missing variables.

Output paths must be relative, contain no `..`, remain within the target root after resolution, and cross no symlink. Templates also stay within their Recipe root. Existing generated paths and overlapping top-level Kotlin declarations are conflicts even when overwrite might appear harmless. Recipes are trusted bundled inputs, not an untrusted plugin system.

Plan JSON contains recipe/version, file before/after/Diff entries, dependency additions, conflicts, adaptation, risks, validation, provenance and already_installed. Human output prints conflicts and unified Diff. Provenance contains full required dependencies, upstream source and inspected Gradle/AGP/Kotlin versions.

`.android-stack/manifest.json` schema 1 records installed Recipe versions, owned file hashes, modified shared files, dependency pins, source metadata and environment. A private journal carries before-images until commit; recover refuses later user edits. There is no automated upgrade or uninstall protocol in V1.


## Image Recipe selection

`coil-standard` requires a Compose-enabled Kotlin module and generates AppImage. `glide-standard` generates `ImageView.loadGlide` and `ImageView.clearGlide` for XML Views or Compose AndroidView. Both require INTERNET permission for the generated image integration. Glide 4.16.0 uses the standard RequestManager API and keeps request options and their JVM tests in the Recipe. The dependency needs no generated Glide API or Compose artifact.

Inspect the selected module's `image_libraries` before planning. Direct coordinates and supported catalog aliases identify Coil 2, Coil 3 and Glide. An existing alternate image library or an owned alternate Recipe blocks installation. Matching versions are reused. Conflicting versions and owned or user-created files require manual review.

Project presets select a UI template tree and one image Recipe. Shared templates supply the ViewModel, Repository, DI and application bootstrap. The `reuses` metadata enumerates eligible dependencies for the preset. Each create invocation installs Retrofit, Timber and the selected image Recipe.

## Existing-project diagnostics

Plans retain the string `conflicts` list for compatibility. The `diagnostics` array contains `category`, `reason`, `action` and `blocking`. A blocked JSON install exits 2 and returns `error` and `diagnostics` on stderr.

| Category | Typical action |
|---|---|
| `environment_missing` | Locate the project root or restore its existing wrapper |
| `project_configuration` | Resolve the selected module or review the Manifest patch |
| `unverified_versions` | Test the exact existing toolchain in isolation |
| `incompatible_versions` | Identify the proven constraint and agree on a remedy before editing versions |
| `dependency_conflict` | Preserve the installed dependency and validate a compatible integration |
| `source_conflict` | Preserve source and review the proposed location or integration manually |

A missing INTERNET declaration includes `path`, `diff` and `authorization_required`. The default plan keeps the edit outside `files`. Both forms of `plan` are read-only.

```sh
android-stack plan --project /path/to/project --recipe retrofit-standard --json
android-stack plan --project /path/to/project --recipe retrofit-standard --add-internet-permission --json
```

After the user explicitly approves the displayed permission change, use `install --add-internet-permission` with the same project, module and Recipe. The installer applies the reviewed insertion in the same transaction as the Recipe files. All other blockers still prevent writes. The flag covers one unrestricted source Manifest declaration. Restricted permissions, merge overrides, malformed XML and repairs to an already installed Recipe require review and an approved manual edit. Verify the merged Manifest for the intended variant.

## Source roots for existing modules

The Inspector reports `selected.source_layout` with separate main and test candidates. Each candidate reports its module-relative path, whether Gradle declares it explicitly, whether the namespace directory exists and the observed Kotlin file count. An unresolved sourceSets configuration is reported as an issue.

The Resolver selects a root for each required source set. It considers literal declared roots first. With conventional roots it prefers an existing namespace directory, then the highest Kotlin file count. A tie blocks installation and names the candidates. When no main root exists, it uses `src/main/kotlin`. When no test root exists, it uses `src/test/java` for a conventional Java main root and `src/test/kotlin` otherwise.

Retrofit, Coil, Glide and Timber use `main_source` and, for Recipes with unit tests, `test_source` in their file paths. The resolved module-relative choices appear as project-relative paths in plan adaptation and file entries. The Installer checks that each target is inside the selected module. A module build script change invalidates the plan even when its existing dependencies were reusable.

Supported custom Kotlin DSL syntax uses `sourceSets.getByName("main") { java.setSrcDirs(listOf("code/main")) }` directly in `android`, or a `sourceSets { getByName(...) { ... } }` block. The same forms support `test`. Dynamic, chained, variant-specific and externally applied declarations require review. Absolute paths, parent traversals and symlinked roots are rejected. [Android source-set documentation](https://developer.android.com/build/build-variants#change-default-source-set-configurations)

Generated projects retain the preset's Kotlin source directories. For an existing installation, status, verify and repeat install use the recorded paths and hashes. Layout inference only applies to a fresh installation of a Recipe. Recover continues to use the journal's exact paths. A migration of owned files would need its own preview, authorization and atomic update to the ownership record.
