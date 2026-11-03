"""Real Android acceptance matrix. No mocked Gradle execution or skipped cases.

Run after generating examples. Requires ANDROID_HOME, Java 17 and Maven access.
Each fixture and its full Gradle log is retained under the requested output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from android_stack_skills.resolver import plan
from android_stack_skills.installer import apply
from android_stack_skills.validator import verify


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()
            and not any(part in ('.gradle', 'build', '.kotlin') for part in p.relative_to(root).parts)
            and p.name not in ('verification.log', 'verification.json')}


def run(output: Path) -> list[dict]:
    repo = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, preset, reinstall in [
        ('clean-compose', 'lightweight', None),
        ('existing-retrofit', 'lightweight', 'retrofit-standard'),
        ('existing-coil', 'lightweight', 'coil-standard'),
        ('existing-timber', 'lightweight', 'timber-standard'),
        ('existing-hilt', 'standard', None),
        ('version-conflict', 'lightweight', 'retrofit-standard'),
    ]:
        root = output/name
        shutil.copytree(repo/'examples'/f'{preset}-app', root,
                        ignore=shutil.ignore_patterns('build', '.gradle', '.kotlin', 'verification.*'))
        if reinstall:
            manifest = root/'.android-stack/manifest.json'
            data = json.loads(manifest.read_text())
            record = data['recipes'].pop(reinstall)
            for path in record['files']:
                (root/path).unlink()
                data.get('managed_files', {}).pop(path, None)
            manifest.write_text(json.dumps(data, indent=2))
        if name == 'version-conflict':
            build = root/'app/build.gradle.kts'
            build.write_text(build.read_text().replace('com.squareup.retrofit2:retrofit:3.0.0','com.squareup.retrofit2:retrofit:2.9.0'))
            before = snapshot(root)
            blocked = plan(root, 'retrofit-standard')
            assert any('Dependency conflict' in c for c in blocked['conflicts']), blocked
            try:
                apply(blocked)
                raise AssertionError('Conflicted install did not fail')
            except Exception as exc:
                from android_stack_skills.errors import StackError
                if not isinstance(exc, StackError):
                    raise
            assert before == snapshot(root)
            result = {'scenario': name, 'success': True, 'conflicts': blocked['conflicts'], 'unchanged': True}
        else:
            if reinstall:
                change = plan(root, reinstall)
                assert not change['conflicts'], change['conflicts']
                assert change['dependencies'] == [], 'Existing matching dependencies should be reused'
                apply(change)
            before = snapshot(root)
            for recipe in ('retrofit-standard', 'coil-standard', 'timber-standard'):
                change = plan(root, recipe)
                assert change['already_installed'] and not change['conflicts'], change['conflicts']
                apply(change)
            assert before == snapshot(root), 'Repeated install changed files'
            result = verify(root)
            result.update(scenario=name, idempotent=True)
            counts = [ET.parse(p).getroot().attrib for p in root.glob('app/build/test-results/testDebugUnitTest/TEST-*.xml')]
            result['tests'] = sum(int(c['tests']) for c in counts)
            result['failures'] = sum(int(c['failures'])+int(c['errors']) for c in counts)
            assert result['tests'] > 0 if result['success'] else True
        results.append(result)
        (output/'results.json').write_text(json.dumps(results, indent=2)+'\n')
        print(json.dumps(result), flush=True)
        if not result['success']:
            raise SystemExit(1)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='New directory for retained test projects/logs')
    run(parser.parse_args().output)
