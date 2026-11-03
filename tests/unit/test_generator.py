from pathlib import Path
import pytest
from android_stack_skills.generator import create_project
from android_stack_skills.errors import StackError
from android_stack_skills.inspector import inspect
from android_stack_skills.installer import status


@pytest.mark.parametrize('preset', ['lightweight', 'standard'])
def test_create(tmp_path, preset):
    target = tmp_path/'Demo'
    result = create_project('Demo', 'com.example.demo', preset, target, False)
    assert result['status'] == 'generated-unverified'
    assert len(status(target)['recipes']) == 3
    assert inspect(target)['selected']['hilt'] == (preset == 'standard')
    assert (target/'gradle/wrapper/gradle-wrapper.jar').stat().st_size > 40000
    with pytest.raises(StackError, match='exists'):
        create_project('Demo', 'com.example.demo', preset, target, False)


@pytest.mark.parametrize('name,package', [('bad name', 'com.example'), ('Demo', 'com.class'), ('Demo', '../escape')])
def test_invalid_name(tmp_path, name, package):
    with pytest.raises(StackError):
        create_project(name, package, 'lightweight', tmp_path/'Demo', False)
    assert not (tmp_path/'Demo').exists()


@pytest.mark.parametrize(
    'ui,image,expected',
    [('compose', None, 'coil'), ('xml', None, 'glide'), ('compose', 'glide', 'glide')],
)
@pytest.mark.parametrize('preset', ['lightweight', 'standard'])
def test_ui_image_selection(tmp_path, ui, image, expected, preset):
    target = tmp_path/'Demo'
    result = create_project('Demo', 'com.example.demo', preset, target, False, ui=ui, image=image)
    assert (result['ui'], result['image']) == (ui, expected)
    assert set(status(target)['recipes']) == {'retrofit-standard', 'timber-standard', f'{expected}-standard'}
    build = (target/'app/build.gradle.kts').read_text()
    assert ('viewBinding = true' in build) == (ui == 'xml')
    assert ('alias(libs.plugins.kotlin.compose)' in build) == (ui == 'compose')


def test_xml_coil_is_rejected_before_writing(tmp_path):
    target = tmp_path/'Demo'
    with pytest.raises(StackError, match=r'XML \+ Coil'):
        create_project('Demo', 'com.example.demo', 'standard', target, False, ui='xml', image='coil')
    assert not target.exists()
