"""Read-only CLI probe, with optional forwarding to the same checked executable."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REQUIREMENTS = Path(__file__).resolve().parent.parent/'cli-requirements.json'


def probe(executable, requirements, environment):
    try:
        process = subprocess.run([executable, 'capabilities', '--json'], env=environment,
                                 capture_output=True, text=True, timeout=15)
        if process.returncode:
            return {'status': 'incompatible', 'reason': 'CLI capability query failed'}
        report = json.loads(process.stdout)
        if not isinstance(report, dict) or report.get('protocol') != requirements['protocol']:
            return {'status': 'incompatible', 'reason': 'Unsupported capability protocol'}
        version = report.get('version')
        if not isinstance(version, str) or not version or version != report.get('distribution_version'):
            return {'status': 'incompatible', 'reason': 'Runtime and installed distribution versions differ or are unavailable'}
        capabilities = report.get('capabilities')
        recipes = report.get('recipes')
        if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities) or not isinstance(recipes, dict):
            return {'status': 'incompatible', 'reason': 'Invalid capability report'}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'status': 'incompatible', 'reason': str(exc)}

    missing = sorted(set(requirements['capabilities']) - set(capabilities))
    mismatched = {name: expected for name, expected in requirements['recipes'].items()
                  if recipes.get(name) != expected}
    return {'status': 'incompatible' if missing or mismatched else 'ready',
            'version': version, 'missing_capabilities': missing, 'required_recipes': mismatched}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', help='Absolute path to a trusted installed android-stack executable')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='Arguments to forward after --')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print(json.dumps({'status': 'unsupported-python', 'requires': '3.11+'}))
        return 2
    if args.cli and not Path(args.cli).is_absolute():
        parser.error('--cli must be an absolute path')
    executable = args.cli or shutil.which('android-stack')
    if not executable or not Path(executable).is_file():
        print(json.dumps({'status': 'missing-cli'}))
        return 2

    executable = str(Path(executable).resolve())
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONUSERBASE')}
    environment['PYTHONNOUSERSITE'] = '1'
    requirements = json.loads(REQUIREMENTS.read_text(encoding='utf-8'))
    result = probe(executable, requirements, environment)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if result['status'] != 'ready' or not command:
        print(json.dumps({**result, 'executable': executable}))
        return 0 if result['status'] == 'ready' else 2
    return subprocess.call([executable, *command], env=environment)


if __name__ == '__main__':
    sys.exit(main())
