from pathlib import Path
from android_stack_skills.manifest import DATA, recipes


def test_package_recipe_copies_are_identical():
    repo = Path(__file__).resolve().parents[2]
    for file in (repo/'recipes').rglob('*'):
        if file.is_file():
            assert file.read_bytes() == (DATA/'recipes'/file.relative_to(repo/'recipes')).read_bytes()
    assert len(recipes()) == 6


def test_all_skills_are_bundled():
    repo = Path(__file__).resolve().parents[2]
    source = sorted((repo/'skills').glob('*/SKILL.md'))
    assert len(source) == 4
    for skill in source:
        assert (DATA/'skills'/skill.relative_to(repo/'skills')).read_bytes() == skill.read_bytes()
