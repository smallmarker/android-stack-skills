"""Check Codex JSONL evidence against actual isolated build/test artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

CASES = {
    'project': ('codex-project-retry', 'agent-project-retry/FreshCompose'),
    'network': ('codex-network-final', 'agent-network-retry'),
    'image': ('codex-image-final', 'agent-image'),
    'logging': ('codex-logging-final', 'agent-logging'),
}


def run(workspace: Path, evidence: Path) -> list[dict]:
    repo = Path(__file__).resolve().parents[1]
    results = []
    for kind, (name, relative) in CASES.items():
        events = [json.loads(line) for line in (evidence/(name+'.jsonl')).read_text().splitlines() if line.strip()]
        completed = [event['item'] for event in events if event['type'] == 'item.completed']
        commands = [item for item in completed if item['type'] == 'command_execution']
        selected = any(f'.agents/skills/android-{kind}/SKILL.md' in item.get('command', '')
                       and item.get('exit_code') == 0 and 'description:' in item.get('aggregated_output', '') for item in commands)
        cli_commands = [dict(command=item['command'], exit_code=item.get('exit_code'))
                        for item in commands if 'android-stack ' in item.get('command', '')]
        root = workspace/relative
        suites = [ET.parse(p).getroot().attrib for p in root.glob('app/build/test-results/testDebugUnitTest/TEST-*.xml')]
        verification = json.loads((root/'.android-stack/verification.json').read_text())
        result = {'skill': 'android-'+kind, 'selected_and_read': selected, 'cli_commands': cli_commands,
                  'session_completed': any(event['type']=='turn.completed' for event in events),
                  'build_success': verification['success'], 'tests': sum(int(s['tests']) for s in suites),
                  'failures': sum(int(s['failures'])+int(s['errors']) for s in suites),
                  'skipped': sum(int(s['skipped']) for s in suites)}
        assert selected and cli_commands and result['session_completed'] and result['build_success'], result
        assert result['tests'] > 0 and result['failures'] == 0 and result['skipped'] == 0
        if kind != 'project':
            protected = ['app/src/main/java/dev/rc/notes/NotesActivity.kt',
                         'app/src/main/java/dev/rc/notes/NotesRepository.kt',
                         'app/src/test/java/dev/rc/notes/NotesRepositoryTest.kt']
            for path in protected:
                assert (root/path).read_bytes() == (repo/'tests/fixtures/rc-notes'/path).read_bytes(), path
            result['protected_business_files_unchanged'] = True
        destination = evidence/('agent-'+kind+'-build.txt')
        shutil.copyfile(root/'.android-stack/verification.log', destination)
        result['build_log_sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
        results.append(result)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.workspace, args.evidence), indent=2, ensure_ascii=False))
