import json
import subprocess
import sys


def call(*args):
    return subprocess.run([sys.executable, '-m', 'android_stack_skills.cli', *map(str,args)], text=True, capture_output=True)


def test_cli_install_flow(project):
    report = call('inspect', '--project', project, '--json')
    assert report.returncode == 0
    assert json.loads(report.stdout)['selected']['language'] == 'kotlin'
    dry = call('install', '--project', project, '--recipe', 'retrofit-standard', '--dry-run', '--json')
    assert dry.returncode == 0 and json.loads(dry.stdout)['files']
    assert not (project/'.android-stack').exists()
    first = call('install', '--project', project, '--recipe', 'retrofit-standard', '--json')
    assert first.returncode == 0
    assert json.loads(first.stdout)['status'] == 'installed-unverified'
    second = call('install', '--project', project, '--recipe', 'retrofit-standard', '--json')
    assert json.loads(second.stdout)['status'] == 'already-installed'
    current = call('status', '--project', project, '--json')
    assert set(json.loads(current.stdout)['recipes']) == {'retrofit-standard'}


def test_invalid_recipe_exit(project):
    result = call('plan', '--project', project, '--recipe', 'missing', '--json')
    assert result.returncode == 2
    assert 'Unknown recipe' in json.loads(result.stderr)['error']
