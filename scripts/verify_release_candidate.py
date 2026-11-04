"""Exercise a reviewed local RC bundle outside the source checkout."""
import argparse
from functools import partial
import hashlib
import http.client
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
from urllib.request import build_opener, ProxyHandler
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    return {p.relative_to(path).as_posix(): digest(p) for p in path.rglob('*') if p.is_file()}


def run_matrix(args):
    root = args.output.resolve()
    root.mkdir()
    home = root/'home'
    home.mkdir()
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'PYTHONNOUSERSITE': '1'}
    base = root/'project'
    shutil.copytree(args.project, base, ignore=shutil.ignore_patterns(
        '.agents', 'AGENTS.md', 'candidate-artifact.json', 'skills-lock.json'))
    original = snapshot(base)
    outcomes = {}

    def run(*command, code=0, note):
        result = subprocess.run([str(x) for x in command], cwd=base, env=env,
                                capture_output=True, text=True, timeout=180)
        (root/f'{note}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == code, (command, result.returncode, result.stderr)
        return result.stdout

    def record(key, detail):
        outcomes[key] = {'result': 'PASS', 'detail': detail}
        (root/'matrix.json').write_text(json.dumps(outcomes, indent=2)+'\n', encoding='utf-8')

    class FixtureServer(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/interrupted':
                self.send_response(200)
                self.send_header('Content-Length', '100')
                self.end_headers()
                self.wfile.write(b'incomplete')
                return
            super().do_GET()

    opener = build_opener(ProxyHandler({}))
    with ThreadingHTTPServer(('127.0.0.1', 0), partial(FixtureServer, directory=args.bundle.parent)) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with opener.open(f'{url}/interrupted', timeout=10) as response:
                response.read()
        except http.client.IncompleteRead as error:
            (root/'download-interrupted.txt').write_text(str(error)+'\n')
        else:
            raise AssertionError('Interrupted HTTP response was accepted')
        assert snapshot(base) == original and not (root/'venv').exists()
        record('08_interrupted_download', 'Local HTTP returned a truncated body; no setup ran.')
        downloaded = root/args.bundle.name
        with opener.open(f'{url}/{args.bundle.name}', timeout=20) as response:
            downloaded.write_bytes(response.read())
        server.shutdown()
    assert digest(downloaded) == args.bundle_sha256
    release = root/'release'
    with zipfile.ZipFile(downloaded) as archive:
        archive.extractall(release)
    manifest_path = release/'release-manifest.json'
    assert digest(manifest_path) == args.manifest_sha256
    manifest = json.loads(manifest_path.read_text())
    assert all(digest(release/name) == checksum for name, checksum in manifest['sha256'].items())
    installer = release/'install_rc.py'
    assert digest(args.old_wheel) == args.old_sha256
    gate = args.project_skill.resolve()/'scripts/cli_gate.py'
    user_gate = args.user_skill.resolve()/'scripts/cli_gate.py'

    def check(script, *options, code=0, note):
        return json.loads(run(sys.executable, '-I', script, *options, code=code, note=note))

    def prepare(where, *options, code=0, interpreter=sys.executable, manifest=manifest_path, note):
        return run(interpreter, '-I', installer, '--manifest', manifest, '--sha256',
                   args.manifest_sha256, '--venv', root/where, *options, code=code, note=note)

    assert check(gate, code=2, note='missing-cli')['status'] == 'missing-cli'
    record('02_cli_missing', 'Sanitized PATH resolves no CLI.')
    assert not (root/'venv').exists() and snapshot(base) == original
    record('09_user_declines', 'Declined approval branch skips preparation, with no venv or writes.')

    prepare('old-python', code=2, interpreter=args.unsupported_python, note='old-python')
    assert 'requires CPython 3.11' in (root/'old-python.txt').read_text()
    assert not (root/'old-python').exists()
    record('12_wrong_python', 'Actual Python 3.9 rejects preparation.')
    run(sys.executable, '-I', '-c',
        "import platform,runpy,sys; platform.machine=lambda:'unsupported'; "
        "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')",
        installer, '--manifest', manifest_path, '--sha256', args.manifest_sha256,
        '--venv', root/'unsupported', code=2, note='unsupported-platform')
    assert 'Unsupported RC platform' in (root/'unsupported-platform.txt').read_text()
    assert not (root/'unsupported').exists()
    record('13_unsupported_platform', 'Platform detection simulated with an unsupported architecture.')

    wheel = release/manifest['wheel']
    original_wheel = wheel.read_bytes()
    wheel.write_bytes(original_wheel + b'corrupt')
    prepare('corrupt-wheel', code=2, note='corrupt-wheel')
    assert 'Artifact SHA-256 mismatch' in (root/'corrupt-wheel.txt').read_text()
    assert not (root/'corrupt-wheel').exists()
    wheel.write_bytes(original_wheel)
    record('06_artifact_hash_error', 'Tampered wheel is rejected before venv creation.')

    wheelhouse = release/'wheelhouse/macos-arm64'
    corrupt_deps = root/'corrupt-dependencies'
    shutil.copytree(wheelhouse, corrupt_deps)
    attrs = next(corrupt_deps.glob('attrs-*.whl'))
    attrs.write_bytes(attrs.read_bytes()+b'corrupt')
    prepare('corrupt-deps-venv', '--wheelhouse', corrupt_deps, code=2, note='corrupt-dependency')
    assert 'DO NOT MATCH THE HASHES' in (root/'corrupt-dependency.txt').read_text()
    assert not (root/'corrupt-deps-venv/bin/android-stack').exists()
    record('07_dependency_hash_error', 'Real pip rejects the changed dependency bytes.')
    assert snapshot(base) == original
    record('16_failure_zero_android_writes', 'Fixture file digests match after all failed preparations.')

    report = json.loads(prepare('venv', note='first-prepare'))
    assert report['status'] == 'created'
    assert report['report']['version'] == report['report']['distribution_version'] == manifest['version']
    assert Path(report['report']['module']).is_relative_to(root/'venv')
    cli = report['cli']
    record('01_first_install', 'Hash-verified HTTP fixture bundle installed into clean site-packages.')
    record('10_user_approves', 'Authorized test branch created the venv and probed it.')
    hashes = snapshot(root/'venv')
    assert json.loads(prepare('venv', note='repeat-prepare'))['status'] == 'reused'
    assert snapshot(root/'venv') == hashes
    record('11_repeat_prepare', 'Repeated preparation reused venv with byte-identical files.')

    for scope, script in (('project', gate), ('user', user_gate)):
        assert check(script, '--cli', cli, note=f'ready-{scope}')['status'] == 'ready'
    assert snapshot(base) == original

    old = root/'legacy'
    run(sys.executable, '-I', '-m', 'venv', old, note='legacy-venv')
    run(old/'bin/python', '-I', '-m', 'pip', '--isolated', 'install', '--no-index',
        '--find-links', wheelhouse, args.old_wheel, note='legacy-prepare')
    old_cli = old/'bin/android-stack'
    legacy_report = json.loads(run(old_cli, 'capabilities', '--json', note='legacy-capabilities'))
    assert legacy_report['version'] == '0.2.0'
    blocked = check(gate, '--cli', old_cli, '--', 'install', '--project', base,
                    '--recipe', 'retrofit-standard', code=2, note='old-cli-new-skill')
    assert blocked['missing_capabilities'] == ['distribution.release-identity.v1']
    record('03_old_cli_new_skill', 'Verified Phase 1 wheel probes successfully but lacks release identity.')
    old_skill = root/'old-skill'
    with zipfile.ZipFile(args.old_wheel) as archive:
        prefix = 'android_stack_skills/data/skills/android-network/'
        for name in archive.namelist():
            if name.startswith(prefix) and not name.endswith('/'):
                dest = old_skill/name.removeprefix(prefix)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))
    assert check(old_skill/'scripts/cli_gate.py', '--cli', cli, note='new-cli-old-skill')['status'] == 'ready'
    record('04_new_cli_old_skill', 'Phase 1 Skill extracted from reviewed wheel accepts RC1.')

    wrong_protocol = root/'protocol-cli'
    payload = json.dumps({**report['report'], 'protocol': 2})
    wrong_protocol.write_text(f'#!{sys.executable}\nprint({payload!r})\n')
    wrong_protocol.chmod(0o755)
    assert check(gate, '--cli', wrong_protocol, code=2, note='protocol-mismatch')['status'] == 'incompatible'
    record('05_protocol_mismatch', 'Gate rejected a fixture reporting protocol 2.')
    change = check(gate, '--cli', cli, '--', 'plan', '--project', base, '--recipe',
                   'retrofit-standard', '--json', note='retrofit-plan')
    assert not change['conflicts']
    assert any('/src/main/java/' in f['path'] and f['path'].endswith('/Network.kt') for f in change['files'])
    assert snapshot(base) == original
    record('14_read_only_retrofit_plan', 'Installed CLI planned Network.kt under the existing Java root; zero writes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'old-wheel', 'project', 'project-skill', 'user-skill', 'unsupported-python', 'output'):
        parser.add_argument(f'--{name}', required=True, type=lambda value: Path(value).resolve())
    for name in ('bundle-sha256', 'manifest-sha256', 'old-sha256'):
        parser.add_argument(f'--{name}', required=True)
    run_matrix(parser.parse_args())
