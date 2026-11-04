from pathlib import Path
import difflib
import json
import re
import xml.etree.ElementTree as ET
from jinja2 import Environment, StrictUndefined
from ..errors import StackError
from ..inspector import inspect
from ..inspector.source_layout import choose_source_root
from ..manifest import get_recipe
from ..utils import digest, module_path, read_text, safe_path
from .compatibility import VERSION_KEYS, version_issue
from .permissions import internet_permission_edit

ENV = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)


def render(template: str, variables: dict) -> str:
    try:
        return ENV.from_string(template).render(**variables)
    except Exception as exc:
        raise StackError(f'Template rendering failed: {exc}') from exc


def file_change(path: str, before: str | None, after: str) -> dict:
    lines = difflib.unified_diff((before or '').splitlines(True), after.splitlines(True),
                                 fromfile=path, tofile=path)
    diff = ''.join(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n' for line in lines)
    return {'path': path, 'before': before, 'after': after, 'diff': diff}


def plan(project: Path, recipe_id: str, module: str | None = None,
         *, add_internet_permission: bool = False) -> dict:
    project = project.resolve()
    recipe = get_recipe(recipe_id)
    result = {
        'recipe': recipe_id, 'version': recipe['version'], 'project': str(project),
        'files': [], 'dependencies': [], 'conflicts': [], 'diagnostics': [],
        'adaptation': {}, 'risks': [], 'validation': recipe['validation'], 'already_installed': False,
        'provenance': {'source': recipe['source'], 'dependencies': recipe['dependencies'],
                       'environment': dict.fromkeys(VERSION_KEYS, 'unknown')},
    }

    def diagnose(category: str, reason: str, action: str, *, blocking: bool = True, **details) -> None:
        result['diagnostics'].append(
            {'category': category, 'reason': reason, 'action': action, 'blocking': blocking, **details}
        )
        result['conflicts' if blocking else 'risks'].append(reason)

    if not any((project/name).is_file() for name in ('settings.gradle.kts', 'settings.gradle')):
        diagnose('environment_missing', 'No settings.gradle(.kts) found',
                 'Select the Android project root containing the existing Gradle settings.')
        return result
    try:
        info = inspect(project, module)
    except StackError as exc:
        diagnose('project_configuration', str(exc), 'Review the Gradle settings and version catalog.')
        return result
    result['provenance']['environment'] = {key: info[key] for key in VERSION_KEYS}
    for limitation in info['limitations']:
        diagnose('project_configuration', limitation, 'Select a supported module or review its Gradle declarations.')
    selected = info['selected']
    if recipe['category'] == 'project':
        diagnose('project_configuration', 'Use create for project presets', 'Choose an installable Recipe.')
        return result
    if selected is None:
        return result
    if selected['language'] != 'kotlin':
        diagnose('project_configuration', 'An explicit Kotlin Android plugin is required',
                 'Inspect the module plugin declaration and resolve aliases before installing.')
    if selected['dsl'] != 'kotlin':
        diagnose('project_configuration', 'V1 installer supports Gradle Kotlin DSL only',
                 'Use a Kotlin DSL module or integrate manually after review.')
    if not re.fullmatch(r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+', selected['package']):
        diagnose('project_configuration', 'A literal valid namespace is required',
                 'Resolve the module namespace before generating source.')
    if recipe['requirements'].get('compose') and selected['compose'] is not True:
        diagnose('project_configuration', 'Compose must be enabled explicitly',
                 'Select a Compose-enabled module or use a Views Recipe.')
    if selected['min_sdk'] == 'unknown' or selected['min_sdk'] < recipe['requirements'].get('min_sdk', 21):
        diagnose('project_configuration', 'Unknown or unsupported minSdk',
                 'Review the module minSdk against the Recipe requirements.')
    variables = {'package': selected['package'], 'package_path': selected['package'].replace('.', '/'),
                 'module': selected['path'], 'hilt': selected['hilt']}
    result['adaptation'] = variables
    issue = version_issue(info, selected, recipe_id)
    if issue:
        diagnose(*issue)
    elif recipe_id != 'retrofit-standard':
        unresolved = ', '.join(key for key in VERSION_KEYS if info[key] == 'unknown')
        if unresolved:
            diagnose('unverified_versions', f'Unresolved toolchain versions ({unresolved})',
                     'Inspect the effective versions and verify the project with its existing toolchain.',
                     blocking=False)
    if not info['wrapper']:
        diagnose('environment_missing', 'Gradle wrapper launcher is missing',
                 'Restore the project’s existing wrapper before running verify.', blocking=False)
    module_root = safe_path(project, selected['path'])

    def module_target(relative: str) -> Path:
        return module_path(project, selected['path'], relative)


    build_path = module_target(selected['build'])
    original_build = read_text(build_path)
    manifest_path = safe_path(project, '.android-stack/manifest.json')
    try:
        record = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'recipes': {}}
    except (ValueError, OSError) as exc:
        raise StackError(f'Invalid installation manifest: {exc}') from exc
    installed = record.get('recipes', {}).get(recipe_id)
    permission_path = selected['path']+'/src/main/AndroidManifest.xml'
    if recipe['category'] in ('network', 'image'):
        target = module_target(permission_path)
        try:
            manifest_before = read_text(target)
            manifest_after = internet_permission_edit(manifest_before)
        except (OSError, ValueError, ET.ParseError) as exc:
            diagnose('project_configuration', f'Cannot inspect or safely edit AndroidManifest.xml: {exc}',
                     'Review the source Manifest and merged permissions. An unrestricted INTERNET declaration belongs under <manifest>.',
                     path=permission_path)
        else:
            if manifest_after is not None:
                approved = add_internet_permission and not installed
                patch = file_change(permission_path, manifest_before, manifest_after)
                action = ('Review the Manifest diff and obtain explicit approval. '
                          'Then install with --add-internet-permission or apply the approved edit manually.')
                if approved:
                    action = 'Review the permission diff included in the authorized installation.'
                elif installed:
                    action = 'Review the Manifest diff and obtain explicit approval for a manual edit, then verify again.'
                diagnose('project_configuration', 'Declare android.permission.INTERNET in AndroidManifest.xml before installing',
                         action, blocking=not approved, path=permission_path, diff=patch['diff'],
                         authorization_required=not approved)
                if approved:
                    result['files'].append(patch)
    if installed:
        result['already_installed'] = True
        recorded_module = installed.get('adaptation', {}).get('module')
        if recorded_module and recorded_module != selected['path']:
            diagnose('project_configuration', f'Recipe is recorded for module {recorded_module}',
                     'Select the recorded module to verify the existing installation.')
            return result
        if installed['version'] != recipe['version']:
            diagnose('dependency_conflict', 'Recipe upgrade requires manual review',
                     'Compare the installed Recipe and owned files before approving an upgrade.')
        for path, expected in installed['files'].items():
            target = safe_path(project, path)
            if not target.is_file() or digest(read_text(target)) != expected:
                diagnose('source_conflict', f'Installed file changed or missing: {path}',
                         'Compare the owned-file hash and retain user edits. Review recovery manually.')
        for dep in recipe['dependencies']:
            existing = selected['dependencies'].get(dep['module'])
            if existing != dep['version']:
                diagnose('dependency_conflict',
                         f"Installed dependency changed or missing: {dep['module']} (existing={existing}, required={dep['version']})",
                         'Review the existing dependency and installed Recipe before editing either.')
        return result
    files = [file for file in recipe['files'] if file.get('when') != 'hilt' or variables['hilt']]
    layout = selected['source_layout']
    try:
        if digest(original_build) != layout['build_sha256']:
            raise StackError(f"File changed during source layout inspection: {selected['build']}")
        if layout['issue']:
            raise StackError(layout['issue'])
        main = choose_source_root(layout['main'], 'main', 'src/main/kotlin')
        variables['main_source'] = str(Path(selected['path'])/main)
        if any('{{ test_source }}' in file['path'] for file in files):
            default_test = 'src/test/java' if main == 'src/main/java' else 'src/test/kotlin'
            test = choose_source_root(layout['test'], 'test', default_test)
            variables['test_source'] = str(Path(selected['path'])/test)
    except StackError as exc:
        diagnose('project_configuration', str(exc), 'Review the module sourceSets and source roots before installing.')
        return result

    result['source_layout_build'] = {'path': selected['build'], 'sha256': layout['build_sha256']}
    if recipe['category'] == 'image':
        requested = recipe_id.removesuffix('-standard')
        existing_libraries = set(selected['image_libraries'])
        for installed_id in ('coil-standard', 'glide-standard'):
            entry = record.get('recipes', {}).get(installed_id, {})
            if entry.get('adaptation', {}).get('module') == selected['path']:
                existing_libraries.add(installed_id.removesuffix('-standard'))
        for library in sorted(existing_libraries - {requested}):
            diagnose('dependency_conflict',
                     f'Existing image library {library} in {selected["name"]}; retain it or review migration manually',
                     'Choose the existing library’s Recipe or review a separately authorized migration.')

    def add_change(relative: str, content: str, generated: bool = True):
        target = module_target(relative)
        old = read_text(target) if target.exists() else None
        if generated and relative.endswith('.kt'):
            symbols = set(re.findall(r'\b(?:class|object|interface|typealias)\s+(\w+)', content))
            package_match = re.search(r'^package\s+([\w.]+)', content, re.M)
            source_set = 'test' if variables.get('test_source') and Path(relative).is_relative_to(variables['test_source']) else 'main'
            for root in layout[source_set]:
                for existing in safe_path(module_root, root['path']).rglob('*.kt'):
                    existing_text = existing.read_text()
                    existing_package = re.search(r'^package\s+([\w.]+)', existing_text, re.M)
                    if package_match and existing_package and package_match[1] == existing_package[1]:
                        existing_symbols = set(re.findall(r'\b(?:class|object|interface|typealias)\s+(\w+)', existing_text))
                        if symbols & existing_symbols:
                            diagnose('source_conflict', f'Existing Kotlin declarations conflict: {existing.relative_to(project)}',
                                     'Keep the existing declarations and review a separate package or manual integration.')
        if generated and old is not None:
            diagnose('source_conflict', f'File already exists: {relative}',
                     'Keep the existing file and review the proposed changes manually.', path=relative)
        if old != content:
            result['files'].append(file_change(relative, old, content))
    additions = []
    for dep in recipe['dependencies']:
        existing = selected['dependencies'].get(dep['module'])
        if existing is not None and existing != dep['version']:
            diagnose('dependency_conflict', f"Dependency conflict {dep['module']}: existing={existing}, required={dep['version']}",
                     'Keep the existing dependency. Validate an adaptation in an isolated project before changing versions.')
        elif existing is None:
            # Unknown catalog aliases or project-specific dependency declarations must not be guessed.
            result['dependencies'].append(dep)
            additions.append(f'    {dep["configuration"]}("{dep["module"]}:{dep["version"]}")')
    if re.search(r'libs\.bundles\.|(?:implementation|api|testImplementation)\s*\((?!\s*(?:"|libs\.|platform\(libs\.))', original_build):
        diagnose('project_configuration', 'Dependency bundles/dynamic declarations require manual dependency review',
                 'Resolve dependency declarations and versions before installing.')
    if additions:
        # Append a standalone, bounded dependencies block: no rewriting arbitrary Kotlin structure.
        if re.search(r'(^|\n)\s*dependencies\s*\{', original_build) is None:
            diagnose('project_configuration', 'No explicit dependencies block recognized',
                     'Identify the module’s dependency declarations and review integration manually.')
        updated = original_build.rstrip()+'\n\n// android-stack: '+recipe_id+'\ndependencies {\n'+'\n'.join(additions)+'\n}\n'
        add_change(selected['build'], updated, False)
    if recipe_id == 'coil-standard':
        for source in selected['sources']:
            if any('ImageLoader' in p.read_text() for p in safe_path(project, source).rglob('*.kt')):
                diagnose('source_conflict', 'Existing ImageLoader configuration needs manual integration',
                         'Keep the existing loader and review how to reuse it.')
    for file in files:
        relative = render(file['path'], variables)
        content = render(safe_path(recipe['_root'], file['template']).read_text(), variables)
        add_change(relative, content)
    result['risks'].append('Generated files require Gradle verification; initialization instructions are in the generated Usage.md')
    return result
