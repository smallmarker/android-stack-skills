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
