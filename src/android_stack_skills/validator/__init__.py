from pathlib import Path
import json
import subprocess
from ..errors import StackError
from ..inspector import inspect
from ..installer import status
from ..manifest import recipes
from ..resolver import plan
from ..utils import safe_path


def verify(project: Path, module: str | None = None, timeout: int = 900) -> dict:
    project = project.resolve()
    recipes()  # validate all bundled manifests
    info = inspect(project, module)
    selected = info['selected']
    if selected is None or not info['wrapper']:
        raise StackError('Verification requires a selected module and executable Gradle wrapper')
    installed = status(project)
    for recipe in installed['recipes']:
        conflicts = plan(project, recipe, selected['name'])['conflicts']
        if conflicts:
            raise StackError('; '.join(conflicts))
    command = [str(project/'gradlew'), selected['name']+':assembleDebug', selected['name']+':testDebugUnitTest', '--console=plain', '--stacktrace']
    output = safe_path(project, '.android-stack/verification.log')
    output.parent.mkdir(exist_ok=True)
    try:
        with output.open('w') as log:
            log.write('COMMAND: '+ ' '.join(command)+'\n')
            log.flush()
            process = subprocess.run(command, cwd=project, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        result = {'success': process.returncode == 0, 'exit_code': process.returncode, 'command': command, 'log': str(output)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        with output.open('a') as log:
            log.write('\n'+str(exc))
        result = {'success': False, 'error': str(exc), 'command': command, 'log': str(output)}
    safe_path(project, '.android-stack/verification.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
