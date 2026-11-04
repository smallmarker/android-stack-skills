import json

import pytest

from android_stack_skills.errors import StackError
from android_stack_skills.installer import apply
from android_stack_skills.resolver import plan
from test_cli_commands import call


def snapshot(project):
    return {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}


@pytest.mark.parametrize('kotlin', ['2.0.21', '2.2.20'])
def test_verified_toolchain_installs_idempotently(project, kotlin):
    build = project/'build.gradle.kts'
    build.write_text(build.read_text().replace('2.2.20', kotlin))
    module = project/'app/build.gradle.kts'
    module.write_text(module.read_text().replace('compose = true', 'compose = false'))
    toolchain = build.read_bytes()
    change = plan(project, 'retrofit-standard')
    assert not change['conflicts']
    assert change['provenance']['environment']['kotlin'] == kotlin
    apply(change)
    installed = snapshot(project)
    assert apply(plan(project, 'retrofit-standard'))['status'] == 'already-installed'
    assert snapshot(project) == installed
    assert build.read_bytes() == toolchain


@pytest.mark.parametrize(('kotlin', 'gradle', 'category'), [
    ('2.1.20', '8.14.3', 'unverified_versions'),
    ('2.0.21', '8.13', 'unverified_versions'),
    ('2.2.20', '8.9', 'incompatible_versions'),
])
def test_version_conflict_blocks_every_write(project, kotlin, gradle, category):
    build = project/'build.gradle.kts'
    build.write_text(build.read_text().replace('2.2.20', kotlin))
    wrapper = project/'gradle/wrapper/gradle-wrapper.properties'
    wrapper.write_text(wrapper.read_text().replace('8.14.3', gradle))
    manifest = project/'app/src/main/AndroidManifest.xml'
    manifest.write_text('<manifest><application/></manifest>\n')
    before = snapshot(project)
    result = call('install', '--project', project, '--recipe', 'retrofit-standard',
                  '--add-internet-permission', '--json')
    assert result.returncode == 2
    assert category in {issue['category'] for issue in json.loads(result.stderr)['diagnostics']}
    assert snapshot(project) == before
    assert not (project/'.android-stack').exists()


def test_legacy_compose_remains_unverified(project):
    build = project/'build.gradle.kts'
    build.write_text(build.read_text().replace('2.2.20', '2.0.21'))
    result = plan(project, 'retrofit-standard')
    assert any(issue['category'] == 'unverified_versions' and issue['blocking'] for issue in result['diagnostics'])


def test_internet_permission_requires_opt_in_and_preserves_manifest(project):
    manifest = project/'app/src/main/AndroidManifest.xml'
    original = (
        b'<?xml version="1.0" encoding="utf-8"?>\r\n'
        b'<manifest xmlns:android="http://schemas.android.com/apk/res/android">\r\n'
        b'    <!-- keep this comment -->\r\n    <application />\r\n</manifest>\r\n'
    )
    manifest.write_bytes(original)
    args = ('--project', project, '--recipe', 'retrofit-standard', '--json')
    planned = call('plan', *args)
    assert planned.returncode == 2
    plan_result = json.loads(planned.stdout)
    permission = next(issue for issue in plan_result['diagnostics'] if issue.get('authorization_required'))
    assert permission['category'] == 'project_configuration'
    assert '+    <uses-permission android:name="android.permission.INTERNET" />' in permission['diff']
    assert all(file['path'] != permission['path'] for file in plan_result['files'])
    assert call('plan', *args, '--add-internet-permission').returncode == 0
    assert call('install', *args).returncode == 2
    assert manifest.read_bytes() == original
    assert not (project/'.android-stack').exists()
    approved = call('install', *args, '--add-internet-permission')
    assert approved.returncode == 0, approved.stderr
    inserted = b'    <uses-permission android:name="android.permission.INTERNET" />\r\n'
    assert manifest.read_bytes().replace(inserted, b'') == original
    before = snapshot(project)
    repeated = call('install', *args)
    assert json.loads(repeated.stdout)['status'] == 'already-installed'
    assert snapshot(project) == before


def test_restricted_permission_requires_manual_review(project):
    manifest = project/'app/src/main/AndroidManifest.xml'
    manifest.write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
        '<uses-permission android:name="android.permission.INTERNET" android:maxSdkVersion="28"/>'
        '<application/></manifest>'
    )
    result = plan(project, 'retrofit-standard', add_internet_permission=True)
    assert any('SDK restriction' in conflict for conflict in result['conflicts'])
    with pytest.raises(StackError):
        apply(result)


def test_missing_project_reports_environment(tmp_path):
    result = plan(tmp_path, 'retrofit-standard')
    assert result['diagnostics'][0]['category'] == 'environment_missing'
    assert result['conflicts']


def test_module_plugin_version_takes_precedence(project):
    module = project/'app/build.gradle.kts'
    module.write_text(
        '// id("org.jetbrains.kotlin.android") version "2.2.20"\n' +
        module.read_text().replace('id("org.jetbrains.kotlin.android")',
                                   'id("org.jetbrains.kotlin.android") version "2.1.20"')
    )
    result = plan(project, 'retrofit-standard')
    assert result['provenance']['environment']['kotlin'] == '2.1.20'
    assert any(issue['category'] == 'unverified_versions' for issue in result['diagnostics'])
