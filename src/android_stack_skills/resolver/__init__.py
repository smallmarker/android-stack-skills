from pathlib import Path
import difflib
import re
from jinja2 import Environment, StrictUndefined
from ..errors import StackError
from ..inspector import inspect
from ..manifest import get_recipe
from ..utils import digest, safe_path
import json

ENV = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)


def render(template: str, variables: dict) -> str:
    try:
        return ENV.from_string(template).render(**variables)
    except Exception as exc:
        raise StackError(f'Template rendering failed: {exc}') from exc


def plan(project: Path, recipe_id: str, module: str | None = None) -> dict:
    project = project.resolve()
    recipe = get_recipe(recipe_id)
    info = inspect(project, module)
    result = {'recipe': recipe_id, 'version': recipe['version'], 'project': str(project),
              'files': [], 'dependencies': [], 'conflicts': list(info['limitations']),
              'adaptation': {}, 'risks': [], 'validation': recipe['validation'], 'already_installed': False, 'provenance': {'source': recipe['source'], 'dependencies': recipe['dependencies'], 'environment': {key: info[key] for key in ('kotlin', 'agp', 'gradle')}}}
    selected = info['selected']
    if recipe['category'] == 'project':
        result['conflicts'].append('Use create for project presets')
        return result
    if selected is None:
        return result
    if selected['language'] != 'kotlin':
        result['conflicts'].append('An explicit Kotlin Android plugin is required')
    if selected['dsl'] != 'kotlin':
        result['conflicts'].append('V1 installer supports Gradle Kotlin DSL only')
    if not re.fullmatch(r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+', selected['package']):
        result['conflicts'].append('A literal valid namespace is required')
    if recipe['requirements'].get('compose') and selected['compose'] is not True:
        result['conflicts'].append('Compose must be enabled explicitly')
    if selected['min_sdk'] == 'unknown' or selected['min_sdk'] < recipe['requirements'].get('min_sdk', 21):
        result['conflicts'].append('Unknown or unsupported minSdk')
    variables = {'package': selected['package'], 'package_path': selected['package'].replace('.', '/'),
                 'module': selected['path'], 'hilt': selected['hilt']}
    result['adaptation'] = variables
    from packaging.version import Version, InvalidVersion
    for key, minimum in [('kotlin', '2.2.20'), ('agp', '8.13.0')]:
        value = info[key]
        if value == 'unknown':
            result['risks'].append(f'{key} version unknown; compatibility requires real build verification')
        else:
            try:
                if Version(value) < Version(minimum):
                    result['conflicts'].append(f'{key} {value} is outside the supported baseline (>= {minimum})')
                if key == 'agp' and Version(value).major >= 9:
                    result['conflicts'].append('AGP 9 built-in Kotlin is outside the V1 support range')
            except InvalidVersion:
                result['conflicts'].append(f'Cannot evaluate {key} version {value}')
    build_path = safe_path(project, selected['build'])
    original_build = build_path.read_text()
    manifest_path = safe_path(project, '.android-stack/manifest.json')
    try:
        record = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'recipes': {}}
    except (ValueError, OSError) as exc:
        raise StackError(f'Invalid installation manifest: {exc}') from exc
    installed = record.get('recipes', {}).get(recipe_id)
    if installed:
        result['already_installed'] = True
        if installed['version'] != recipe['version']:
            result['conflicts'].append('Recipe upgrade requires manual review')
        for path, expected in installed['files'].items():
            target = safe_path(project, path)
            if not target.is_file() or digest(target.read_text()) != expected:
                result['conflicts'].append(f'Installed file changed or missing: {path}')
        for dep in recipe['dependencies']:
            existing = selected['dependencies'].get(dep['module'])
            if existing != dep['version']:
                result['conflicts'].append(f"Installed dependency changed or missing: {dep['module']} (existing={existing}, required={dep['version']})")
        return result
    if recipe['category'] == 'image':
        requested = recipe_id.removesuffix('-standard')
        existing_libraries = set(selected['image_libraries'])
        for installed_id in ('coil-standard', 'glide-standard'):
            entry = record.get('recipes', {}).get(installed_id, {})
            if entry.get('adaptation', {}).get('module') == selected['path']:
                existing_libraries.add(installed_id.removesuffix('-standard'))
        for library in sorted(existing_libraries - {requested}):
            result['conflicts'].append(
                f'Existing image library {library} in {selected["name"]}; retain it or review migration manually'
            )

    def add_change(relative: str, content: str, generated: bool = True):
        target = safe_path(project, relative)
        old = target.read_text() if target.exists() else None
        if generated and relative.endswith('.kt'):
            symbols = set(re.findall(r'\b(?:class|object|interface|typealias)\s+(\w+)', content))
            package_match = re.search(r'^package\s+([\w.]+)', content, re.M)
            for source in selected['sources']:
                for existing in safe_path(project, source).rglob('*.kt'):
                    existing_text = existing.read_text()
                    existing_package = re.search(r'^package\s+([\w.]+)', existing_text, re.M)
                    if package_match and existing_package and package_match[1] == existing_package[1]:
                        existing_symbols = set(re.findall(r'\b(?:class|object|interface|typealias)\s+(\w+)', existing_text))
                        if symbols & existing_symbols:
                            result['conflicts'].append(f'Existing Kotlin declarations conflict: {existing.relative_to(project)}')
        if generated and old is not None:
            result['conflicts'].append(f'File already exists: {relative}')
        if old != content:
            result['files'].append({'path': relative, 'before': old, 'after': content,
                'diff': ''.join(difflib.unified_diff((old or '').splitlines(True), content.splitlines(True), fromfile=relative, tofile=relative))})
    additions = []
    for dep in recipe['dependencies']:
        existing = selected['dependencies'].get(dep['module'])
        if existing is not None and existing != dep['version']:
            result['conflicts'].append(f"Dependency conflict {dep['module']}: existing={existing}, required={dep['version']}")
        elif existing is None:
            # Unknown catalog aliases or project-specific dependency declarations must not be guessed.
            result['dependencies'].append(dep)
            additions.append(f'    {dep["configuration"]}("{dep["module"]}:{dep["version"]}")')
    if re.search(r'libs\.bundles\.|(?:implementation|api|testImplementation)\s*\((?!\s*(?:"|libs\.|platform\(libs\.))', original_build):
        result['conflicts'].append('Dependency bundles/dynamic declarations require manual dependency review')
    if additions:
        # Append a standalone, bounded dependencies block: no rewriting arbitrary Kotlin structure.
        if re.search(r'(^|\n)\s*dependencies\s*\{', original_build) is None:
            result['conflicts'].append('No explicit dependencies block recognized')
        updated = original_build.rstrip()+'\n\n// android-stack: '+recipe_id+'\ndependencies {\n'+'\n'.join(additions)+'\n}\n'
        add_change(selected['build'], updated, False)
    if recipe['category'] in ('network', 'image'):
        manifest = selected['path']+'/src/main/AndroidManifest.xml'
        target = safe_path(project, manifest)
        import xml.etree.ElementTree as ET
        try:
            document = ET.fromstring(target.read_text())
            permissions = {node.get('{http://schemas.android.com/apk/res/android}name') for node in document.findall('uses-permission')}
            if 'android.permission.INTERNET' not in permissions:
                result['conflicts'].append('Declare android.permission.INTERNET in AndroidManifest.xml before installing')
        except (OSError, ET.ParseError) as exc:
            result['conflicts'].append(f'Cannot inspect AndroidManifest.xml: {exc}')
    if recipe_id == 'coil-standard':
        for source in selected['sources']:
            if any('ImageLoader' in p.read_text() for p in safe_path(project, source).rglob('*.kt')):
                result['conflicts'].append('Existing ImageLoader configuration needs manual integration')
    for file in recipe['files']:
        if file.get('when') == 'hilt' and not variables['hilt']:
            continue
        relative = render(file['path'], variables)
        content = render(safe_path(recipe['_root'], file['template']).read_text(), variables)
        add_change(relative, content)
    result['risks'].append('Generated files require Gradle verification; initialization instructions are in the generated Usage.md')
    return result
