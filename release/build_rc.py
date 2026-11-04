"""Build a committed RC using pinned build tools and pre-fetched dependency wheels."""
import argparse
from importlib import metadata
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile

from install_rc import digest


def git(*args):
    return subprocess.check_output(['git', *args])


def package(commit, wheelhouses, output):
    for name, expected in {'pip': '25.3', 'setuptools': '80.9.0'}.items():
        if metadata.version(name) != expected:
            raise ValueError(f'Build requires {name}=={expected}')
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 11):
        raise ValueError('Build requires CPython 3.11')

    commit = git('rev-parse', '--verify', f'{commit}^{{commit}}').decode().strip()
    epoch = git('show', '-s', '--format=%ct', commit).decode().strip()
    archive = git('archive', '--format=tar', commit)
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter='data')
        version = tomllib.loads((source/'pyproject.toml').read_text())['project']['version']
        output.mkdir(parents=True, exist_ok=False)
        subprocess.run(
            [sys.executable, '-I', '-m', 'pip', '--isolated', 'wheel', '--no-index',
             '--no-deps', '--no-build-isolation', '--no-cache-dir', '--wheel-dir', str(output), '.'],
            cwd=source, check=True, env={**os.environ, 'SOURCE_DATE_EPOCH': epoch},
        )
        wheel = output/f'android_stack_skills-{version}-py3-none-any.whl'
        shutil.copy2(source/'release/install_rc.py', output)
        shutil.copytree(source/'release/locks', output/'locks')

        for lock in sorted((output/'locks').glob('*.txt')):
            expected_hashes = {line.split('--hash=sha256:', 1)[1].strip()
                               for line in lock.read_text().splitlines() if line and not line.startswith('#')}
            dependencies = sorted((wheelhouses/lock.stem).glob('*.whl'))
            if len(dependencies) != len(expected_hashes) or {digest(p) for p in dependencies} != expected_hashes:
                raise ValueError(f'Wheelhouse does not match lock: {lock.stem}')
            target = output/'wheelhouse'/lock.stem
            target.mkdir(parents=True)
            for dependency in dependencies:
                shutil.copy2(dependency, target)

        skills = output/f'android-stack-skills-{version}-skills.zip'
        write_zip(skills, source/'skills')
        with zipfile.ZipFile(wheel) as archive, zipfile.ZipFile(skills) as bundle:
            for name in bundle.namelist():
                if archive.read(f'android_stack_skills/data/skills/{name}') != bundle.read(name):
                    raise ValueError(f'Skill bundle differs from wheel: {name}')
        manifest = {
            'schema': 1, 'version': version, 'git_commit': commit, 'source_date_epoch': int(epoch),
            'build': {'python': sys.version.split()[0], 'pip': metadata.version('pip'),
                      'setuptools': metadata.version('setuptools')},
            'wheel': wheel.name, 'skills': skills.name,
            'sha256': {p.relative_to(output).as_posix(): digest(p)
                       for p in sorted(output.rglob('*')) if p.is_file()},
        }
        (output/'release-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        (output/'SHA256SUMS').write_text(''.join(
            f'{digest(p)}  {p.relative_to(output).as_posix()}\n'
            for p in sorted(output.rglob('*')) if p.is_file()), encoding='utf-8')
        write_zip(output.parent/f'android-stack-skills-{version}-{output.name}.zip', output)


def write_zip(destination, root):
    with zipfile.ZipFile(destination, 'w') as archive:
        for path in sorted(p for p in root.rglob('*') if p.is_file()):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix())
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--wheelhouses', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    package(args.commit, args.wheelhouses.resolve(), args.output.resolve())
