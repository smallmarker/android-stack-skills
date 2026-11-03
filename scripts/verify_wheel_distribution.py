"""Validate installed wheel resources from outside the source checkout.

Run using the independent venv that installed the wheel. No source imports or
editable install are needed. Creates deliberately unverified packaging fixtures.
"""
import argparse
import json
from importlib.resources import files
from pathlib import Path
from android_stack_skills.generator import create_project
from android_stack_skills.manifest import recipes
import android_stack_skills


def run(output: Path) -> dict:
    if output.exists():
        raise ValueError('Output must not exist')
    output.mkdir(parents=True)
    resource = files('android_stack_skills').joinpath('data')
    skills = sorted(p.name for p in resource.joinpath('skills').iterdir() if p.joinpath('SKILL.md').is_file())
    assert skills == ['android-image', 'android-logging', 'android-network', 'android-project']
    recipe_count = len(recipes())
    assert recipe_count == 6
    for relative in ('recipe.schema.json', 'gradle-wrapper.jar', 'licenses/Gradle-LICENSE.txt', 'project-templates/.gitignore.j2'):
        assert resource.joinpath(relative).is_file(), relative
    projects = []
    for preset in ('lightweight', 'standard'):
        for ui in ('compose', 'xml'):
            result = create_project(
                'Wheel'+preset.title(), 'dev.wheel.'+preset, preset, output/f'{preset}-{ui}', False, ui=ui
            )
            project = Path(result['project'])
            assert (project/'.gitignore').is_file()
            assert (project/f'app/src/main/kotlin/dev/wheel/{preset}/MainActivity.kt').is_file()
            assert (project/'app/src/main/res/layout/activity_main.xml').is_file() == (ui == 'xml')
            projects.append(result)
    return {'module': android_stack_skills.__file__, 'skills': skills, 'recipe_count': recipe_count,
            'projects': projects, 'note': 'Packaging generation only; run real verify separately.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(run(parser.parse_args().output), indent=2))
