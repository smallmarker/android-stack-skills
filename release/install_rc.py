"""Prepare an approved Android Stack RC in an isolated CPython environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def target():
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 11):
        raise ValueError('RC preparation requires CPython 3.11')
    machine = platform.machine().lower()
    if sys.platform == 'darwin' and machine in ('arm64', 'x86_64'):
        version = tuple(map(int, platform.mac_ver()[0].split('.')[:2]))
        floor = (11, 0) if machine == 'arm64' else (10, 15)
        if version >= floor:
            return f'macos-{machine}'
    if sys.platform == 'linux' and machine == 'x86_64':
        libc, version = platform.libc_ver()
        if libc == 'glibc' and tuple(map(int, version.split('.')[:2])) >= (2, 28):
            return 'linux-x86_64'
    if sys.platform == 'win32' and machine in ('amd64', 'x86_64'):
        return 'windows-x86_64'
    raise ValueError(f'Unsupported RC platform: {sys.platform}/{machine}')


def verified_file(root, manifest, name):
    path = root / name
    if not path.resolve().is_relative_to(root) or digest(path) != manifest['sha256'][name]:
        raise ValueError(f'Artifact SHA-256 mismatch: {name}')
    return path


def prepare(manifest_path, expected_hash, environment, wheelhouse):
    platform_key = target()
    lock_name = f'locks/{platform_key}.txt'
    if digest(manifest_path) != expected_hash:
        raise ValueError('Release manifest SHA-256 mismatch')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['schema'] != 1:
        raise ValueError('Unsupported release manifest schema')
    root = manifest_path.parent
    wheel = verified_file(root, manifest, manifest['wheel'])
    lock = verified_file(root, manifest, lock_name)
    if wheelhouse is None:
        wheelhouse = root / 'wheelhouse' / platform_key
    if not wheelhouse.is_dir():
        raise ValueError('Wheelhouse is not a directory')
    scripts = environment / ('Scripts' if sys.platform == 'win32' else 'bin')
    suffix = '.exe' if sys.platform == 'win32' else ''
    python = scripts / f'python{suffix}'
    cli = scripts / f'android-stack{suffix}'
    receipt = environment / 'android-stack-release.sha256'
    child_env = {k: v for k, v in os.environ.items()
                 if not k.upper().startswith(('PYTHON', 'PIP_'))}
    child_env.update(PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE='1')
    if environment.exists():
        if not receipt.is_file() or receipt.read_text().strip() != expected_hash:
            raise ValueError('Environment already exists without a matching receipt. Choose a new path.')
        status = 'reused'
    else:
        venv.EnvBuilder(with_pip=True).create(environment)
        requirement = environment / 'android-stack-wheel.txt'
        requirement.write_text(
            f'{wheel.as_uri()} --hash=sha256:{manifest["sha256"][manifest["wheel"]]}\n',
            encoding='utf-8',
        )
        subprocess.run(
            [str(python), '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check',
             'install', '--no-input', '--no-cache-dir', '--only-binary=:all:', '--require-hashes',
             '--no-index', '--find-links', str(wheelhouse), '-r', str(lock), '-r', str(requirement)],
            check=True, env=child_env, stdout=sys.stderr,
        )
        status = 'created'
    report = json.loads(subprocess.check_output(
        [str(cli), 'capabilities', '--json'], env=child_env, text=True, timeout=30))
    if (report['version'] != manifest['version'] or report['distribution_version'] != manifest['version']
            or not Path(report['module']).resolve().is_relative_to(environment)
            or 'distribution.release-identity.v1' not in report['capabilities']):
        raise ValueError('Installed CLI does not match the release manifest')
    if status == 'created':
        receipt.write_text(expected_hash + '\n')
    return {'status': status, 'cli': str(cli), 'report': report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256', required=True, help='Previously approved manifest SHA-256')
    parser.add_argument('--venv', type=Path, required=True, help='Dedicated directory outside the Android project')
    parser.add_argument('--wheelhouse', type=Path, help='Use only this local dependency directory')
    args = parser.parse_args()
    try:
        result = prepare(args.manifest.resolve(), args.sha256, args.venv.resolve(),
                         args.wheelhouse.resolve() if args.wheelhouse is not None else None)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'RC preparation stopped: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
