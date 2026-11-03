import json
import pytest
from android_stack_skills.validator import verify
from android_stack_skills.installer import recover
from android_stack_skills.utils import digest
from android_stack_skills.errors import StackError


def test_subprocess_failure_is_preserved(project):
    wrapper = project/'gradlew'
    wrapper.write_text('#!/bin/sh\necho "test failure details"\nexit 7\n')
    wrapper.chmod(0o755)
    result = verify(project)
    assert not result['success'] and result['exit_code'] == 7
    assert 'test failure details' in (project/'.android-stack/verification.log').read_text()


def test_recover_restores_journal(tmp_path):
    (tmp_path/'.android-stack').mkdir()
    (tmp_path/'a.txt').write_text('new')
    journal = {'files': [{'path': 'a.txt', 'before': 'old', 'after_hash': digest('new')}], 'manifest': None}
    (tmp_path/'.android-stack/journal.json').write_text(json.dumps(journal))
    recover(tmp_path)
    assert (tmp_path/'a.txt').read_text() == 'old'
    assert not (tmp_path/'.android-stack/journal.json').exists()


def test_recover_protects_later_user_edit(tmp_path):
    (tmp_path/'.android-stack').mkdir()
    (tmp_path/'a.txt').write_text('user')
    journal = {'files': [{'path': 'a.txt', 'before': 'old', 'after_hash': digest('new')}], 'manifest': None}
    (tmp_path/'.android-stack/journal.json').write_text(json.dumps(journal))
    with pytest.raises(StackError, match='user changes'):
        recover(tmp_path)
    assert (tmp_path/'a.txt').read_text() == 'user'


def test_recover_refuses_live_install_lock(tmp_path):
    import os
    (tmp_path/'.android-stack').mkdir()
    (tmp_path/'.android-stack/lock').write_text(str(os.getpid()))
    (tmp_path/'.android-stack/journal.json').write_text('{}')
    with pytest.raises(StackError, match='still active'):
        recover(tmp_path)
    assert (tmp_path/'.android-stack/lock').exists()
