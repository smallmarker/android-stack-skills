"""RC acceptance on an independently authored Android app, using the installed CLI.

Requires Python 3.11+, the wheel installed in this interpreter, JDK/SDK and Maven.
The fixture never calls create or copies generated application code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from android_stack_skills.generator import WRAPPER_HASH
from android_stack_skills.manifest import DATA


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()
            and not any(part in ('build', '.gradle', '.kotlin', '.idea') for part in p.relative_to(root).parts)
            and p.name not in ('verification.log', 'verification.json')}


def run(output: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo/'tests/fixtures/rc-notes', output)
    wrapper = output/'gradle/wrapper'
    wrapper.mkdir()
    jar = (DATA/'gradle-wrapper.jar').read_bytes()
    assert hashlib.sha256(jar).hexdigest() == WRAPPER_HASH
    (wrapper/'gradle-wrapper.jar').write_bytes(jar)
    (wrapper/'gradle-wrapper.properties').write_text(
        'distributionUrl=https\\://services.gradle.org/distributions/gradle-8.14.3-bin.zip\n'
        'distributionSha256Sum=bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531\n')
    launcher = output/'gradlew'
    launcher.write_text('#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nexec java -classpath gradle/wrapper/gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain "$@"\n')
    launcher.chmod(0o755)
    protected = snapshot(output)
    # The module build file is the one intentional existing-file change.
    protected.pop('app/build.gradle.kts')
    evidence = output/'rc-evidence'
    evidence.mkdir()
    results = []

    def cli(*args: str) -> dict:
        command = [sys.executable, '-m', 'android_stack_skills.cli', *args, '--project', str(output), '--json']
        p = subprocess.run(command, capture_output=True, text=True, timeout=1000)
        if p.returncode:
            raise RuntimeError(f'{command}: exit {p.returncode}\n{p.stdout}\n{p.stderr}')
        return json.loads(p.stdout)

    def build(stage: str) -> None:
        result = cli('verify')
        assert result['success']
        shutil.copyfile(output/'.android-stack/verification.log', evidence/(stage+'-build.txt'))
        suites = [ET.parse(p).getroot().attrib for p in output.glob('app/build/test-results/testDebugUnitTest/TEST-*.xml')]
        result.update(stage=stage, tests=sum(int(s['tests']) for s in suites),
                      failures=sum(int(s['failures'])+int(s['errors']) for s in suites),
                      skipped=sum(int(s['skipped']) for s in suites))
        assert result['tests'] > 0 and result['failures'] == 0 and result['skipped'] == 0
        current = snapshot(output)
        assert all(current.get(path) == expected for path, expected in protected.items())
        result['original_files_preserved'] = True
        results.append(result)
        (evidence/'results.json').write_text(json.dumps(results, indent=2)+'\n')
        print(json.dumps(result), flush=True)

    build('baseline')
    for recipe in ('retrofit-standard', 'coil-standard', 'timber-standard'):
        change = cli('plan', '--recipe', recipe)
        assert not change['conflicts']
        (evidence/(recipe+'-plan.json')).write_text(json.dumps(change, indent=2)+'\n')
        assert cli('install', '--recipe', recipe)['status'] == 'installed-unverified'
        before = snapshot(output)
        assert cli('install', '--recipe', recipe)['status'] == 'already-installed'
        assert before == snapshot(output)
        build(recipe)
    (evidence/'status.json').write_text(json.dumps(cli('status'), indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='Must be a new directory')
    run(parser.parse_args().output.resolve())
