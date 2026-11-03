from pathlib import Path
import pytest
from android_stack_skills.errors import StackError
from android_stack_skills.inspector import inspect
from android_stack_skills.manifest import load_recipe
from android_stack_skills.utils import safe_path
from android_stack_skills.resolver import render


def test_inspect(project):
    info = inspect(project)
    assert info['android']
    assert info['selected']['package'] == 'com.example.demo'
    assert info['selected']['min_sdk'] == 26
    assert info['kotlin'] == 'unknown'


def test_non_android(tmp_path):
    with pytest.raises(StackError, match='settings'):
        inspect(tmp_path)


def test_schema(tmp_path):
    path = tmp_path/'recipe.yaml'
    path.write_text('id: invalid')
    with pytest.raises(StackError, match='name'):
        load_recipe(path)


def test_paths(tmp_path):
    for path in ('../escape', '/tmp/absolute'):
        with pytest.raises(StackError):
            safe_path(tmp_path, path)
    (tmp_path/'link').symlink_to('/tmp')
    with pytest.raises(StackError):
        safe_path(tmp_path, 'link/file')


def test_strict_template():
    with pytest.raises(StackError, match='rendering'):
        render('{{ missing }}', {})
    assert render('{{ package }}', {'package': 'com.example'}) == 'com.example'


def test_generated_recipe_schema_is_strict(tmp_path):
    import yaml
    from android_stack_skills.manifest import get_recipe
    recipe = get_recipe('retrofit-standard').copy()
    recipe.pop('_root')
    recipe['dependencies'][0]['configuration'] = 'executeShell'
    path = tmp_path/'recipe.yaml'
    path.write_text(yaml.safe_dump(recipe))
    with pytest.raises(StackError, match='configuration'):
        load_recipe(path)


def test_custom_settings_mapping_is_blocked(project):
    settings = project/'settings.gradle.kts'
    settings.write_text(settings.read_text()+'project(":app").projectDir = file("other")')
    assert any('projectDir' in c for c in inspect(project)['limitations'])
