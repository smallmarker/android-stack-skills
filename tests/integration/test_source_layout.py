from pathlib import Path
import shutil

import pytest

from android_stack_skills.errors import StackError
from android_stack_skills.inspector import inspect
from android_stack_skills.installer import apply, status
from android_stack_skills.resolver import plan

PACKAGE = 'com/example/demo'


def snapshot(project):
    return {path.relative_to(project): path.read_bytes()
            for path in project.rglob('*') if path.is_file()}


@pytest.mark.parametrize(('main', 'test'), [('java', 'java'), ('kotlin', 'kotlin'), ('java', 'kotlin')])
def test_plan_and_install_preserve_source_roots(project, main, test):
    if main == 'kotlin':
        (project/'app/src/main/java').rename(project/'app/src/main/kotlin')
    (project/f'app/src/test/{test}/{PACKAGE}').mkdir(parents=True)
    before = snapshot(project)
    result = plan(project, 'retrofit-standard')
    expected = {f'app/src/main/{main}/{PACKAGE}/network/Network.kt',
                f'app/src/test/{test}/{PACKAGE}/network/NetworkTest.kt'}
    assert expected <= {file['path'] for file in result['files']}
    assert snapshot(project) == before
    apply(result)
    installed = snapshot(project)
    assert expected <= {str(path) for path in installed}
    new_files = {Path(file['path']) for file in result['files'] if file['before'] is None}
    assert set(installed) - set(before) == new_files | {Path('.android-stack/manifest.json')}
    assert apply(plan(project, 'retrofit-standard'))['status'] == 'already-installed'
    assert snapshot(project) == installed


def test_missing_test_root_follows_main_java_convention(project):
    result = plan(project, 'retrofit-standard')
    assert result['adaptation']['test_source'] == 'app/src/test/java'


def test_package_presence_beats_unrelated_kotlin_sources(project):
    other = project/'app/src/main/kotlin/elsewhere'
    other.mkdir(parents=True)
    (other/'Other.kt').write_text('package elsewhere\nclass Other')
    assert plan(project, 'retrofit-standard')['adaptation']['main_source'] == 'app/src/main/java'


def test_kotlin_distribution_breaks_tie(project):
    other = project/f'app/src/main/kotlin/{PACKAGE}'
    other.mkdir(parents=True)
    (other/'Other.kt').write_text('package com.example.demo\nclass Other')
    assert plan(project, 'retrofit-standard')['adaptation']['main_source'] == 'app/src/main/kotlin'


@pytest.mark.parametrize('scope', ['main', 'test'])
def test_ambiguous_layout_stops_install(project, scope):
    for kind in ('java', 'kotlin'):
        (project/f'app/src/{scope}/{kind}/{PACKAGE}').mkdir(parents=True, exist_ok=True)
    before = snapshot(project)
    result = plan(project, 'retrofit-standard')
    assert any(f'Ambiguous {scope} source roots' in conflict for conflict in result['conflicts'])
    with pytest.raises(StackError):
        apply(result)
    assert snapshot(project) == before
    assert not (project/'.android-stack').exists()


def test_literal_custom_main_and_test_roots(project):
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+'''
android {
    sourceSets.getByName("main") { java.setSrcDirs(listOf("code/main")) }
    sourceSets { getByName("test") { java.setSrcDirs(listOf("code/unit")) } }
}
''')
    layout = inspect(project)['selected']['source_layout']
    assert layout['main'][0]['path'] == 'code/main'
    assert layout['main'][0]['declared']
    result = plan(project, 'retrofit-standard')
    assert not result['conflicts']
    apply(result)
    assert (project/f'app/code/main/{PACKAGE}/network/Network.kt').is_file()
    assert (project/f'app/code/unit/{PACKAGE}/network/NetworkTest.kt').is_file()


@pytest.mark.parametrize('declaration', [
    'sourceSets.getByName("main") { java.setSrcDirs(listOf(customDir)) }',
    'sourceSets.getByName("main") { java.setSrcDirs(listOf("../shared")) }',
    'sourceSets.getByName("main") { java.setSrcDirs(listOf("/tmp/external")) }',
    'sourceSets.getByName("main") { java.setSrcDirs(listOf("code/main")) }.also { configure(it) }',
])
def test_unresolved_or_unsafe_source_sets_stop_install(project, declaration):
    build = project/'app/build.gradle.kts'
    build.write_text(build.read_text()+f'\nandroid {{ {declaration} }}\n')
    before = snapshot(project)
    assert inspect(project)['selected']['source_layout']['issue']
    with pytest.raises(StackError):
        apply(plan(project, 'retrofit-standard'))
    assert snapshot(project) == before


def test_other_source_root_test_declaration_conflict(project):
    other = project/'app/src/test/kotlin/suite/Existing.kt'
    other.parent.mkdir(parents=True)
    other.write_text('package com.example.demo.network\nclass NetworkTest')
    (project/f'app/src/test/java/{PACKAGE}').mkdir(parents=True)
    before = snapshot(project)
    result = plan(project, 'retrofit-standard')
    assert any('Existing Kotlin declarations conflict' in conflict for conflict in result['conflicts'])
    with pytest.raises(StackError):
        apply(result)
    assert snapshot(project) == before


def test_old_kotlin_record_wins_over_new_layout(project):
    shutil.rmtree(project/'app/src/main/java')
    result = plan(project, 'retrofit-standard')
    result['adaptation'].pop('main_source')
    result['adaptation'].pop('test_source')
    apply(result)
    java = project/f'app/src/main/java/{PACKAGE}'
    java.mkdir(parents=True)
    for name in ('First', 'Second'):
        (java/f'{name}.kt').write_text(f'package com.example.demo\nclass {name}')
    before = snapshot(project)
    recorded = status(project)
    assert set(recorded['managed_file_status'].values()) == {'ok'}
    assert apply(plan(project, 'retrofit-standard'))['status'] == 'already-installed'
    assert status(project) == recorded
    assert snapshot(project) == before
    assert not (project/f'app/src/main/java/{PACKAGE}/network/Network.kt').exists()


def test_installer_rejects_plan_target_outside_selected_module(project):
    result = plan(project, 'retrofit-standard')
    result['files'][0]['path'] = 'other/src/main/java/Unexpected.kt'
    before = snapshot(project)
    with pytest.raises(StackError, match='inside module'):
        apply(result)
    assert snapshot(project) == before
    assert not (project/'.android-stack').exists()


def test_source_set_change_invalidates_plan_even_when_dependencies_are_reused(project):
    build = project/'app/build.gradle.kts'
    initial = plan(project, 'retrofit-standard')
    dependency_change = next(file for file in initial['files'] if file['path'] == 'app/build.gradle.kts')
    build.write_text(dependency_change['after'])
    result = plan(project, 'retrofit-standard')
    assert not result['dependencies']
    assert all(file['path'] != 'app/build.gradle.kts' for file in result['files'])
    build.write_text(build.read_text()+
                     '\nandroid { sourceSets.getByName("main") { java.setSrcDirs(listOf("code/main")) } }\n')
    before = snapshot(project)
    with pytest.raises(StackError, match='changed since plan'):
        apply(result)
    assert snapshot(project) == before


def test_target_file_conflict_preserves_every_file(project):
    target = project/f'app/src/main/java/{PACKAGE}/network/Network.kt'
    target.parent.mkdir()
    target.write_text('package com.example.demo.network\n// user-owned file\n')
    before = snapshot(project)
    result = plan(project, 'retrofit-standard')
    assert any('File already exists' in conflict for conflict in result['conflicts'])
    with pytest.raises(StackError):
        apply(result)
    assert snapshot(project) == before
    assert not (project/'.android-stack').exists()
