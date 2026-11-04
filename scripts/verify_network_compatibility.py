"""Build the Retrofit Recipe through the CLI on two independently created toolchains.

Run with ANDROID_HOME and JDK 17. Use a new output directory for the fixtures and logs.
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
from verify_rc_incremental import snapshot


def fixture(project: Path, kotlin: str, jvm: int) -> None:
    module = project/'app'
    (module/'src/main').mkdir(parents=True)
    (project/'settings.gradle.kts').write_text(
        'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n'
        'dependencyResolutionManagement { repositories { google(); mavenCentral() } }\n'
        'rootProject.name = "NetworkCompatibility"\ninclude(":app")\n'
    )
    (project/'build.gradle.kts').write_text(f'''plugins {{
    id("com.android.application") version "8.13.1" apply false
    id("org.jetbrains.kotlin.android") version "{kotlin}" apply false
}}
''')
    (project/'gradle.properties').write_text('android.useAndroidX=true\norg.gradle.jvmargs=-Xmx1536m\n')
    (module/'build.gradle.kts').write_text(f'''plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}
android {{
    namespace = "dev.compat.network"
    compileSdk = 36
    defaultConfig {{ minSdk = 24; targetSdk = 36 }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_{jvm}
        targetCompatibility = JavaVersion.VERSION_{jvm}
    }}
    kotlinOptions {{ jvmTarget = "{jvm}" }}
}}
dependencies {{}}
''')
    (module/'src/main/AndroidManifest.xml').write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <application />\n</manifest>\n'
    )
    example = Path(__file__).resolve().parents[1]/'examples/lightweight-app'
    shutil.copytree(example/'gradle/wrapper', project/'gradle/wrapper')
    shutil.copy2(example/'gradlew', project/'gradlew')
    jar = project/'gradle/wrapper/gradle-wrapper.jar'
    assert hashlib.sha256(jar.read_bytes()).hexdigest() == WRAPPER_HASH


def check(project: Path, kotlin: str, jvm: int) -> dict:
    fixture(project, kotlin, jvm)
    original = snapshot(project)
    protected = {path: checksum for path, checksum in original.items()
                 if path not in ('app/build.gradle.kts', 'app/src/main/AndroidManifest.xml')}

    def cli(command: str, *options: str, exit_code: int = 0) -> dict:
        process = subprocess.run(
            [sys.executable, '-m', 'android_stack_skills.cli', command, '--project', str(project),
             '--recipe', 'retrofit-standard', '--json', *options],
            capture_output=True, text=True, timeout=950,
        )
        if process.returncode != exit_code:
            raise RuntimeError(f'{command} exited {process.returncode}\n{process.stdout}\n{process.stderr}')
        return json.loads(process.stdout or process.stderr)

    refused = cli('install', exit_code=2)
    assert any(issue.get('authorization_required') for issue in refused['diagnostics'])
    assert snapshot(project) == original
    reviewed = cli('plan', '--add-internet-permission')
    assert not reviewed['conflicts']
    assert snapshot(project) == original
    installed = cli('install', '--add-internet-permission', '--verify')
    assert installed['verification']['success']
    after = snapshot(project)
    assert all(after[path] == checksum for path, checksum in protected.items())
    assert cli('install')['status'] == 'already-installed'
    assert snapshot(project) == after

    suites = [ET.parse(path).getroot().attrib
              for path in project.glob('app/build/test-results/testDebugUnitTest/TEST-*.xml')]
    counts = {key: sum(int(suite[key]) for suite in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] > 0 and not any(counts[key] for key in ('failures', 'errors', 'skipped'))
    return {'kotlin': kotlin, 'jvm_target': jvm, 'agp': '8.13.1', 'gradle': '8.14.3',
            'toolchain_files_preserved': True, 'idempotent': True, **counts, **installed['verification']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    for kotlin, jvm in (('2.0.21', 11), ('2.2.20', 17)):
        print(json.dumps(check(args.output/f'kotlin-{kotlin}', kotlin, jvm)), flush=True)
