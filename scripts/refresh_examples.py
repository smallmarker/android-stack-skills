"""Maintainer-only: regenerate committed examples, preserving ignored build caches."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
from android_stack_skills.generator import create_project

root = Path(__file__).resolve().parents[1]
for preset in ('lightweight', 'standard'):
    with TemporaryDirectory() as directory:
        output = Path(directory)/'app'
        create_project(preset.title()+'Demo', 'com.example.'+preset, preset, output, False)
        target = root/'examples'/f'{preset}-app'
        for source in output.rglob('*'):
            if source.is_file():
                destination = target/source.relative_to(output)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
