import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_cli_commands import call

SKILLS = Path(__file__).resolve().parents[2]/'skills'
GATE = SKILLS/'android-network/scripts/cli_gate.py'


def test_capability_report_matches_all_skill_contracts():
    version = call('version')
    result = call('capabilities', '--json')
    assert version.returncode == result.returncode == 0
    report = json.loads(result.stdout)
    assert version.stdout.strip() == report['version']
    assert Path(report['python']).resolve() == Path(sys.executable).resolve()
    for contract in SKILLS.glob('*/cli-requirements.json'):
        required = json.loads(contract.read_text())
        assert report['protocol'] == required['protocol']
        assert set(required['capabilities']) <= set(report['capabilities'])
        assert all(report['recipes'][key] == value for key, value in required['recipes'].items())


@pytest.mark.parametrize('failure', ['missing_feature', 'recipe_version', 'metadata_version', 'bad_protocol'])
def test_gate_blocks_forwarding_with_same_release_label(tmp_path, failure):
    contract = json.loads((GATE.parent.parent/'cli-requirements.json').read_text())
    report = {'protocol': 1, 'version': '0.2.0', 'distribution_version': '0.2.0',
              'capabilities': contract['capabilities'], 'recipes': contract['recipes']}
    if failure == 'missing_feature':
        report['capabilities'] = ['workflow.plan-install-verify.v1']
    elif failure == 'recipe_version':
        report['recipes'] = {'retrofit-standard': '0.1.0'}
    elif failure == 'metadata_version':
        report['distribution_version'] = '0.1.0'
    else:
        report['protocol'] = 2

    executable = tmp_path/'android-stack'
    marker = tmp_path/'forwarded'
    executable.write_text(
        f'#!{sys.executable}\n'
        'import sys\nfrom pathlib import Path\n'
        f'if sys.argv[1:] == ["capabilities", "--json"]: print({json.dumps(report)!r})\n'
        f'else: Path({str(marker)!r}).touch()\n'
    )
    executable.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(GATE), '--cli', str(executable), '--', 'install'],
        cwd=tmp_path, text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)['status'] == 'incompatible'
    assert not marker.exists()
