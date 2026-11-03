"""Optimistic concurrency, exclusive lock and persistent rollback journal."""
from pathlib import Path
from contextlib import contextmanager
import json
import os
from ..errors import StackError
from ..utils import digest, safe_path


@contextmanager
def locked(project: Path):
    folder = safe_path(project, '.android-stack')
    folder.mkdir(mode=0o700, exist_ok=True)
    lock = safe_path(project, '.android-stack/lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise StackError('Another operation holds .android-stack/lock; recover an interrupted operation first') from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def apply(plan: dict) -> dict:
    if plan['conflicts']:
        raise StackError('Installation blocked: '+'; '.join(plan['conflicts']))
    if plan['already_installed']:
        return {'status': 'already-installed', 'recipe': plan['recipe']}
    project = Path(plan['project'])
    with locked(project):
        journal_path = safe_path(project, '.android-stack/journal.json')
        if journal_path.exists():
            raise StackError('Pending rollback journal; run recover first')
        manifest = safe_path(project, '.android-stack/manifest.json')
        old_manifest = manifest.read_text() if manifest.exists() else None
        for file in plan['files']:
            path = safe_path(project, file['path'])
            current = path.read_text() if path.exists() else None
            if current != file['before']:
                raise StackError(f"File changed since plan: {file['path']}")
        journal = {'files': [{'path': f['path'], 'before': f['before'], 'after_hash': digest(f['after'])} for f in plan['files']], 'manifest': old_manifest}
        fd = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as journal_file:
            json.dump(journal, journal_file, indent=2)
        try:
            for file in plan['files']:
                path = safe_path(project, file['path'])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(file['after'])
            record = json.loads(old_manifest) if old_manifest else {'schema': 1, 'recipes': {}}
            # Track generated source/test/usage files, not shared build scripts that other recipes extend.
            owned = {f['path']: digest(f['after']) for f in plan['files'] if f['before'] is None}
            record['recipes'][plan['recipe']] = {'version': plan['version'], 'files': owned,
                'dependencies': plan['provenance']['dependencies'], 'source': plan['provenance']['source'],
                'environment': plan['provenance']['environment'], 'adaptation': plan['adaptation'],
                'modified': {f['path']: digest(f['after']) for f in plan['files'] if f['before'] is not None}}
            record.setdefault('managed_files', {}).update({f['path']: digest(f['after']) for f in plan['files']})
            manifest.write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
        except BaseException:
            _restore(project, journal)
            journal_path.unlink(missing_ok=True)
            raise
        journal_path.unlink()
    return {'status': 'installed-unverified', 'recipe': plan['recipe']}


def _restore(project: Path, journal: dict) -> None:
    for file in reversed(journal['files']):
        path = safe_path(project, file['path'])
        if file['before'] is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(file['before'])
    manifest = safe_path(project, '.android-stack/manifest.json')
    if journal['manifest'] is None:
        manifest.unlink(missing_ok=True)
    else:
        manifest.write_text(journal['manifest'])


def recover(project: Path) -> dict:
    project = project.resolve()
    lock = safe_path(project, '.android-stack/lock')
    if lock.exists():
        try:
            owner = int(lock.read_text())
            if owner <= 0:
                raise ValueError('Invalid lock owner')
        except ValueError as exc:
            raise StackError('Cannot determine lock owner; inspect the interrupted process before recovery') from exc
        try:
            os.kill(owner, 0)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            raise StackError('Lock owner may still be active; recovery refused') from exc
        else:
            raise StackError('Lock owner is still active; recovery refused')
    journal_path = safe_path(project, '.android-stack/journal.json')
    if not journal_path.exists():
        raise StackError('No pending journal')
    journal = json.loads(journal_path.read_text())
    for file in journal['files']:
        path = safe_path(project, file['path'])
        if path.exists() and digest(path.read_text()) not in (file['after_hash'], digest(file['before'] or '')):
            raise StackError(f"Recovery would overwrite user changes: {file['path']}")
    _restore(project, journal)
    journal_path.unlink()
    safe_path(project, '.android-stack/lock').unlink(missing_ok=True)
    return {'status': 'recovered'}


def status(project: Path) -> dict:
    path = safe_path(project, '.android-stack/manifest.json')
    record = json.loads(path.read_text()) if path.exists() else {'recipes': {}}
    for recipe in record['recipes'].values():
        recipe['file_status'] = {name: 'ok' if safe_path(project, name).is_file() and digest(safe_path(project, name).read_text()) == expected else 'changed-or-missing' for name, expected in recipe['files'].items()}
    record['managed_file_status'] = {name: 'ok' if safe_path(project, name).is_file() and digest(safe_path(project, name).read_text()) == expected else 'changed-or-missing' for name, expected in record.get('managed_files', {}).items()}
    return record
