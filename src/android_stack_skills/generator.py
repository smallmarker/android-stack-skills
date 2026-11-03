"""Project bootstrap combines shared templates with one UI and image recipe."""
from pathlib import Path
import hashlib
import re
import shutil
from .errors import StackError
from .manifest import DATA, get_recipe
from .resolver import render, plan
from .installer import apply
from .utils import safe_path
from .validator import verify

WRAPPER_HASH = '7d3a4ac4de1c32b59bc6a4eb8ecb8e612ccd0cf1ae1e99f66902da64df296172'
DISTRIBUTION_HASH = 'bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531'
KEYWORDS = {'class', 'fun', 'package', 'object', 'when', 'in', 'is', 'val', 'var', 'interface', 'return', 'this', 'super', 'null', 'true', 'false', 'if', 'else', 'for', 'while', 'try', 'catch', 'throw', 'as', 'break', 'continue', 'do', 'import', 'typealias', 'typeof'}


def create_project(name: str, package: str, preset: str, output: Path, validate: bool = True,
                   *, ui: str = 'compose', image: str | None = None) -> dict:
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name):
        raise StackError('Project name must be a simple identifier (1–64 characters)')
    if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+', package) or any(part in KEYWORDS for part in package.split('.')):
        raise StackError('Package must be a lowercase dotted identifier without Kotlin keywords')
    defaults = {'compose': 'coil', 'xml': 'glide'}
    if ui not in defaults:
        raise StackError(f'Unsupported UI: {ui}')
    image = defaults[ui] if image is None else image
    if image not in ('coil', 'glide'):
        raise StackError(f'Unsupported image library: {image}')
    if ui == 'xml' and image == 'coil':
        raise StackError('XML + Coil is not supported by create: coil-standard requires Compose. Choose --image glide.')
    recipe = get_recipe(preset)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise StackError('Output already exists; refusing to overwrite')
    if not output.parent.is_dir():
        raise StackError('Output parent must exist')
    variables = {'name': name, 'package': package, 'package_path': package.replace('.', '/'), 'hilt': preset == 'standard', 'ui': ui, 'image': image}
    wrapper = (DATA/'gradle-wrapper.jar').read_bytes()
    if hashlib.sha256(wrapper).hexdigest() != WRAPPER_HASH:
        raise StackError('Bundled Gradle wrapper checksum mismatch')
    output.mkdir()
    try:
        for template_root in (DATA/'project-templates', DATA/'project-ui'/ui):
            for template in sorted(template_root.rglob('*.j2')):
                relative = render(str(template.relative_to(template_root))[:-3], variables)
                target = safe_path(output, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(render(template.read_text(), variables))
        if variables['hilt']:
            target = safe_path(output, f'app/src/main/kotlin/{variables["package_path"]}/di/AppModule.kt')
            target.parent.mkdir(parents=True)
            target.write_text(render('''package {{ package }}.di

import {{ package }}.data.DefaultHomeRepository
import {{ package }}.data.HomeRepository
import {{ package }}.network.NetworkConfig
import {{ package }}.network.TokenProvider
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides fun repository(impl: DefaultHomeRepository): HomeRepository = impl
    @Provides fun config(): NetworkConfig = NetworkConfig("https://example.com/")
    @Provides fun tokens(): TokenProvider = TokenProvider { null }
}
''', variables))
        for file in recipe['files']:
            target = safe_path(output, render(file['path'], variables))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render(safe_path(recipe['_root'], file['template']).read_text(), variables))
        wrapper_dir = output/'gradle/wrapper'
        wrapper_dir.mkdir(exist_ok=True)
        (wrapper_dir/'gradle-wrapper.jar').write_bytes(wrapper)
        shutil.copyfile(DATA/'licenses/Gradle-LICENSE.txt', wrapper_dir/'Gradle-LICENSE.txt')
        (wrapper_dir/'gradle-wrapper.properties').write_text(
            'distributionBase=GRADLE_USER_HOME\ndistributionPath=wrapper/dists\n'
            'distributionUrl=https\\://services.gradle.org/distributions/gradle-8.14.3-bin.zip\n'
            f'distributionSha256Sum={DISTRIBUTION_HASH}\nnetworkTimeout=10000\nvalidateDistributionUrl=true\nzipStoreBase=GRADLE_USER_HOME\nzipStorePath=wrapper/dists\n')
        (output/'gradlew').write_text('#!/bin/sh\nset -eu\nAPP_HOME=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nif [ -n "${JAVA_HOME:-}" ]; then JAVA="$JAVA_HOME/bin/java"; else JAVA=java; fi\nexec "$JAVA" -classpath "$APP_HOME/gradle/wrapper/gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain "$@"\n')
        (output/'gradlew').chmod(0o755)
        (output/'gradlew.bat').write_text('@echo off\r\nset "JAVA_EXE=java.exe"\r\nif defined JAVA_HOME set "JAVA_EXE=%JAVA_HOME%\\bin\\java.exe"\r\n"%JAVA_EXE%" -classpath "%~dp0gradle\\wrapper\\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*\r\n')
        for recipe_id in ('retrofit-standard', f'{image}-standard', 'timber-standard'):
            apply(plan(output, recipe_id))
    except BaseException:
        shutil.rmtree(output)
        raise
    result = {'project': str(output), 'preset': preset, 'ui': ui, 'image': image, 'status': 'generated-unverified'}
    if validate:
        # Build failures preserve the complete generated project and diagnostic logs.
        result['verification'] = verify(output)
        result['status'] = 'verified' if result['verification']['success'] else 'verification-failed'
    return result
