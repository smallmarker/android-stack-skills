"""Exercise offline CLI readiness using reviewed wheels and installed Skill fixtures.

Prepare candidate/, legacy/, wheelhouse/, agent-project/.agents/skills/ and
home-user/.agents/skills/ in a new temporary root. See docs/agent-compatibility.md.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys



def main(root: Path, unsupported_python: Path) -> None:
    home=root/'clean-home'
    home.mkdir()
    project=root/'isolated-android'
    project.mkdir()
    (project/'settings.gradle.kts').write_text('include(":app")\n')
    env={'HOME':str(home),'PATH':'/usr/bin:/bin','PYTHONNOUSERSITE':'1'}
    python=sys.executable
    project_gate=root/'agent-project/.agents/skills/android-network/scripts/cli_gate.py'
    user_gate=root/'home-user/.agents/skills/android-network/scripts/cli_gate.py'
    wheelhouse=root/'wheelhouse'
    wheelname='android_stack_skills-0.2.0-py3-none-any.whl'
    candidate=root/'candidate'/wheelname
    expected=hashlib.sha256(candidate.read_bytes()).hexdigest()

    def run(args, expected_code=0):
        result=subprocess.run([str(a) for a in args],cwd=project,env=env,
                              capture_output=True,text=True,timeout=75)
        assert result.returncode==expected_code,(args,result.returncode,result.stdout,result.stderr)
        return result.stdout

    def snapshot(path):
        return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in path.rglob('*') if p.is_file()}

    def gate(script, cli=None, command=(), code=0, interpreter=python):
        args=[interpreter,'-I',script]
        if cli:
            args.extend(['--cli',cli])
        if command:
            args.extend(['--',*command])
        return json.loads(run(args,code))

    def install(venv, wheel, source, code=0):
        run([python,'-I','-m','venv',venv])
        return run([venv/'bin/python','-I','-m','pip','--isolated','install','--no-index',
                    '--only-binary=:all:','--find-links',source,wheel],code)

    def prepare(approved):
        venv=root/'approved'
        executable=venv/'bin/android-stack'
        if executable.exists():
            assert gate(project_gate,executable)['status']=='ready'
            return 'reused'
        if not approved:
            return 'declined'
        assert hashlib.sha256(candidate.read_bytes()).hexdigest()==expected
        install(venv,candidate,wheelhouse)
        assert gate(project_gate,executable)['status']=='ready'
        return 'created'

    before=snapshot(project)
    results={}
    results['missing_cli']=gate(project_gate,code=2)['status']
    assert results['missing_cli']=='missing-cli'
    results['python_3_9']=gate(project_gate,code=2,interpreter=unsupported_python)['status']
    assert results['python_3_9']=='unsupported-python'
    legacy=root/'legacy-env'
    install(legacy,root/'legacy'/wheelname,wheelhouse)
    legacy_cli=legacy/'bin/android-stack'
    results['legacy_version']=run([legacy_cli,'version']).strip()
    results['legacy_status']=gate(project_gate,legacy_cli,command=['install','--project',project,'--recipe','retrofit-standard'],code=2)['status']
    assert results['legacy_status']=='incompatible'
    results['approval_declined']=prepare(False)
    assert results['approval_declined']=='declined' and not (root/'approved').exists()
    failed=root/'failed-env'
    empty=root/'empty-wheelhouse'
    empty.mkdir()
    install(failed,candidate,empty,code=1)
    assert not (failed/'bin/android-stack').exists()
    results['failed_preparation_project_unchanged']=snapshot(project)==before
    assert results['failed_preparation_project_unchanged']
    results['approval_granted']=prepare(True)
    cli=root/'approved/bin/android-stack'
    report=json.loads(run([cli,'capabilities','--json']))
    assert Path(report['module']).is_relative_to(root/'approved')
    assert report['version']==results['legacy_version']==report['distribution_version']
    results['candidate_version']=report['version']
    results['candidate_module']=report['module']
    results['project_skill_gate']=gate(project_gate,cli)['status']
    results['user_skill_gate']=gate(user_gate,cli)['status']
    for script in (project_gate,user_gate):
        recipes=gate(script,cli,command=['recipes','list','--json'])
        assert any(r['id']=='retrofit-standard' for r in recipes)
    results['forwarding_from_both_scopes']=True
    venv_before=snapshot(root/'approved')
    results['repeat_prepare']=prepare(True)
    assert results['repeat_prepare']=='reused'
    assert snapshot(root/'approved')==venv_before and snapshot(project)==before
    results['android_project_unchanged']=True
    results['candidate_sha256']=expected
    results['wheelhouse_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(wheelhouse.glob('*.whl'))}
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--unsupported-python', type=Path, required=True)
    args = parser.parse_args()
    main(args.fixtures.resolve(), args.unsupported_python)
