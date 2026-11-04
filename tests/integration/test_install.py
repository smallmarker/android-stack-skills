import json
import pytest
from android_stack_skills.errors import StackError
from android_stack_skills.resolver import plan
from android_stack_skills.installer import apply, status


@pytest.mark.parametrize('recipe', ['retrofit-standard', 'coil-standard', 'glide-standard', 'timber-standard'])
def test_roundtrip(project, recipe):
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    change = plan(project, recipe)
    assert not change['conflicts']
    assert change['files']
    assert {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()} == before
    apply(change)
    snapshot = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    repeated = plan(project, recipe)
    assert repeated['already_installed'] and not repeated['conflicts']
    apply(repeated)
    assert snapshot == {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    assert set(status(project)['recipes']) == {recipe}


def test_conflicting_version(project):
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'\ndependencies { implementation("com.squareup.retrofit2:retrofit:2.9.0") }')
    change = plan(project, 'retrofit-standard')
    assert any('Dependency conflict' in x for x in change['conflicts'])
    with pytest.raises(StackError):
        apply(change)
    assert not (project/'.android-stack').exists()


def test_matching_dependency(project):
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'\ndependencies { implementation("com.squareup.retrofit2:retrofit:3.0.0") }')
    change = plan(project, 'retrofit-standard')
    assert not change['conflicts']
    assert not any(d['module'] == 'com.squareup.retrofit2:retrofit' for d in change['dependencies'])


def test_concurrent_edit(project):
    change = plan(project, 'retrofit-standard')
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'// user edit')
    with pytest.raises(StackError, match='changed since plan'):
        apply(change)
    assert not (project/'app/src/main/java/com/example/demo/network/Network.kt').exists()


def test_file_conflict(project):
    file = project/'app/src/main/java/com/example/demo/network/Network.kt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('// user source')
    assert any('already exists' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_owned_file_edit(project):
    apply(plan(project, 'retrofit-standard'))
    source = project/'app/src/main/java/com/example/demo/network/Network.kt'
    source.write_text('// modified')
    assert any('changed or missing' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_rollback(project, monkeypatch):
    from pathlib import Path
    change = plan(project, 'retrofit-standard')
    original = Path.write_text
    def fail_manifest(self, *args, **kwargs):
        if self.name == 'manifest.json':
            raise OSError('simulated disk error')
        return original(self, *args, **kwargs)
    original_build = (project/'app/build.gradle.kts').read_text()
    monkeypatch.setattr(Path, 'write_text', fail_manifest)
    with pytest.raises(OSError, match='disk error'):
        apply(change)
    assert (project/'app/build.gradle.kts').read_text() == original_build
    assert not (project/'app/src/main/java/com/example/demo/network/Network.kt').exists()


def test_installed_dependency_removed(project):
    apply(plan(project, 'retrofit-standard'))
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text().replace('    implementation("com.squareup.retrofit2:retrofit:3.0.0")\n', ''))
    assert any('dependency changed or missing' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_version_catalog_existing_dependency(project):
    folder = project/'gradle'
    folder.mkdir(exist_ok=True)
    (folder/'libs.versions.toml').write_text('[versions]\nretrofit="2.9.0"\n[libraries]\nretrofit = { module="com.squareup.retrofit2:retrofit", version.ref="retrofit" }\n')
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'\ndependencies { implementation(libs.retrofit) }')
    assert any('existing=2.9.0' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_multi_module_requires_selection(project):
    (project/'settings.gradle.kts').write_text('include(":app", ":other")')
    (project/'other').mkdir()
    (project/'other/build.gradle.kts').write_text((project/'app/build.gradle.kts').read_text())
    assert plan(project, 'retrofit-standard')['conflicts']
    assert not plan(project, 'retrofit-standard', ':app')['conflicts']


def test_groovy_is_read_only(project):
    path = project/'app/build.gradle.kts'
    path.rename(path.with_suffix(''))
    assert any('Kotlin DSL' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_dynamic_dependency_is_blocked(project):
    path = project/'app/build.gradle.kts'
    path.write_text(path.read_text()+'\ndependencies { implementation(customNetwork) }')
    assert any('dynamic' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_no_kotlin_plugin_is_blocked(project):
    path = project/'app/build.gradle.kts'
    path.write_text(path.read_text().replace('id("org.jetbrains.kotlin.android")',''))
    assert any('Kotlin Android plugin' in c for c in plan(project, 'retrofit-standard')['conflicts'])


def test_same_declaration_in_java_source_root_is_blocked(project):
    source = project/'app/src/main/java/com/example/demo/logging/Existing.kt'
    source.parent.mkdir()
    source.write_text('package com.example.demo.logging\nobject AppLogger {}')
    assert any('declarations conflict' in c for c in plan(project, 'timber-standard')['conflicts'])


def test_permission_comment_is_not_permission(project):
    manifest = project/'app/src/main/AndroidManifest.xml'
    manifest.write_text('<manifest><!-- android.permission.INTERNET --><application/></manifest>')
    assert any('INTERNET' in c for c in plan(project, 'retrofit-standard')['conflicts'])


@pytest.mark.parametrize(('coordinate', 'recipe', 'existing'), [
    ('com.github.bumptech.glide:glide:4.16.0', 'coil-standard', 'glide'),
    ('io.coil-kt:coil:2.7.0', 'glide-standard', 'coil'),
    ('io.coil-kt.coil3:coil-compose:3.3.0', 'glide-standard', 'coil'),
])
def test_other_image_library_is_preserved(project, coordinate, recipe, existing):
    build = project/'app/build.gradle.kts'
    before = build.read_text()+f'\ndependencies {{ implementation("{coordinate}") }}'
    build.write_text(before)
    change = plan(project, recipe)
    assert any(f'Existing image library {existing}' in c for c in change['conflicts'])
    with pytest.raises(StackError):
        apply(change)
    assert build.read_text() == before
    assert not (project/'.android-stack').exists()


@pytest.mark.parametrize(('version', 'conflict'), [('4.16.0', False), ('4.15.1', True)])
def test_glide_catalog_version(project, version, conflict):
    gradle = project/'gradle'
    gradle.mkdir(exist_ok=True)
    (gradle/'libs.versions.toml').write_text(f'[libraries]\nglide = "com.github.bumptech.glide:glide:{version}"\n')
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'\ndependencies { implementation(libs.glide) }')
    change = plan(project, 'glide-standard')
    assert bool(change['conflicts']) == conflict
    assert all(dep['module'] != 'com.github.bumptech.glide:glide' for dep in change['dependencies'])


def test_glide_does_not_overwrite_user_wrapper(project):
    source = project/'app/src/main/java/com/example/demo/image/GlideImages.kt'
    source.parent.mkdir(parents=True)
    original = 'package com.example.demo.image\n// Existing image helpers\n'
    source.write_text(original)
    change = plan(project, 'glide-standard')
    assert any('File already exists' in conflict for conflict in change['conflicts'])
    with pytest.raises(StackError):
        apply(change)
    assert source.read_text() == original
    assert not (project/'.android-stack').exists()


def test_existing_coil_record_can_be_verified_with_glide_present(project):
    apply(plan(project, 'coil-standard'))
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'\ndependencies { implementation("com.github.bumptech.glide:glide:4.16.0") }')
    repeated = plan(project, 'coil-standard')
    assert repeated['already_installed']
    assert not repeated['conflicts']
    assert not repeated['files']
    assert any('Existing image library coil' in c for c in plan(project, 'glide-standard')['conflicts'])
