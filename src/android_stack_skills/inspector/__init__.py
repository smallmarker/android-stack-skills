"""Conservative inspection: unresolved values stay unknown."""
from pathlib import Path
import re
import tomllib
from ..errors import StackError


COORDINATE = re.compile(r'["\']([\w.-]+:[\w.-]+):([^"\'\s]+)["\']')


def image_libraries(dependencies: dict[str, str]) -> list[str]:
    groups = {coordinate.partition(':')[0] for coordinate in dependencies}
    return [
        library for library, recognized in (
            ('coil', {'io.coil-kt', 'io.coil-kt.coil3'}),
            ('glide', {'com.github.bumptech.glide'}),
        )
        if groups & recognized
    ]


def inspect(project: Path, module: str | None = None) -> dict:
    project = project.resolve()
    settings = next((p for p in (project/'settings.gradle.kts', project/'settings.gradle') if p.is_file()), None)
    if settings is None:
        raise StackError('No settings.gradle(.kts) found')
    catalog_file = project/'gradle/libs.versions.toml'
    try:
        catalog = tomllib.loads(catalog_file.read_text()) if catalog_file.exists() else {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise StackError(f'Invalid version catalog: {exc}') from exc
    versions = catalog.get('versions', {})
    dependencies = {}
    aliases = {}
    for alias, entry in catalog.get('libraries', {}).items():
        if isinstance(entry, str):
            pieces = entry.split(':')
            if len(pieces) == 3:
                aliases[alias.replace('-', '.').replace('_', '.')] = (':'.join(pieces[:2]), pieces[2])
            continue
        coordinate = entry.get('module') or f"{entry.get('group', '')}:{entry.get('name', '')}"
        version = entry.get('version', 'unknown')
        if isinstance(version, dict):
            version = versions.get(version.get('ref'), 'unknown')
        aliases[alias.replace('-', '.').replace('_', '.')] = (coordinate, str(version))
    modules = []
    # Inspect only literal includes. Dynamic settings are deliberately not evaluated.
    includes = re.findall(r'include\s*\(([^)]*)\)', settings.read_text())
    names = re.findall(r'["\'](:[\w:-]+)["\']', ' '.join(includes))
    if settings.suffix != '.kts':
        names += re.findall(r"include\s+['\"](:[\w:-]+)['\"]", settings.read_text())
    for name in dict.fromkeys(names):
        base = project / name.lstrip(':').replace(':', '/')
        build = next((p for p in (base/'build.gradle.kts', base/'build.gradle') if p.is_file()), None)
        if not build:
            continue
        text = build.read_text()
        android = bool(re.search(r'com\.android\.(application|library)|libs\.plugins\.android\.(application|library)', text))
        if not android:
            continue
        deps = dict(COORDINATE.findall(text))
        for alias in re.findall(r'libs\.([\w.]+)', text):
            if alias in aliases:
                coordinate, version = aliases[alias]
                deps[coordinate] = version
        namespace = re.search(r'namespace\s*(?:=\s*)?["\']([\w.]+)["\']', text)
        minimum = re.search(r'minSdk(?:Version)?\s*(?:=\s*)?(\d+)', text)
        modules.append({'name': name, 'path': str(base.relative_to(project)), 'build': str(build.relative_to(project)),
                        'dsl': 'kotlin' if build.suffix == '.kts' else 'groovy',
                        'language': 'kotlin' if re.search(r'org\.jetbrains\.kotlin\.android|libs\.plugins\.kotlin\.android|kotlin\("android"\)', text) else 'unknown',
                        'package': namespace.group(1) if namespace else 'unknown',
                        'min_sdk': int(minimum.group(1)) if minimum else 'unknown',
                        'compose': True if re.search(r'compose\s*=\s*true', text) else False if re.search(r'compose\s*=\s*false', text) else 'unknown',
                        'compose_bom': deps.get('androidx.compose:compose-bom', 'unknown'),
                        'view_binding': bool(re.search(r'viewBinding\s*=\s*true', text)),
                        'xml_layouts': any((base/'src/main/res').glob('layout*/*.xml')),
                        'image_libraries': image_libraries(deps),
                        'dependencies': deps, 'hilt': bool(re.search(r'com\.google\.dagger\.hilt\.android|libs\.plugins\.hilt', text)),
                        'sources': [str(p.relative_to(project)) for p in (base/'src/main/java', base/'src/main/kotlin') if p.is_dir()]})
    dependencies.update({k: v for m in modules for k, v in m['dependencies'].items()})
    root_text = (project/'build.gradle.kts').read_text() if (project/'build.gradle.kts').exists() else ''
    def plugin_version(plugin: str, version_key: str) -> str:
        found = re.search(r'id\("'+re.escape(plugin)+r'"\)\s+version\s+"([^"]+)"', root_text)
        return found.group(1) if found else str(versions.get(version_key, 'unknown'))
    wrapper = project/'gradle/wrapper/gradle-wrapper.properties'
    wrapper_text = wrapper.read_text() if wrapper.exists() else ''
    match = re.search(r'gradle-([\d.]+)-(?:bin|all)', wrapper_text)
    chosen = [m for m in modules if module is None or m['name'] == ':'+module.strip(':')]
    limitations = []
    if 'projectDir' in settings.read_text() or 'includeBuild' in settings.read_text():
        limitations.append('Custom projectDir/includeBuild mappings require manual adaptation')
    if not modules:
        limitations.append('No literal Android module recognized; dynamic settings/custom plugin conventions require manual adaptation')
    if len(chosen) != 1:
        limitations.append('Select exactly one Android module with --module')
    return {'project': str(project), 'android': bool(modules), 'settings': settings.name,
            'catalog': str(catalog_file.relative_to(project)) if catalog_file.exists() else 'unknown',
            'kotlin': plugin_version('org.jetbrains.kotlin.android', 'kotlin'),
            'agp': plugin_version('com.android.application', 'agp'), 'gradle': match.group(1) if match else 'unknown',
            'wrapper': (project/'gradlew').is_file(), 'modules': modules,
            'selected': chosen[0] if len(chosen) == 1 else None,
            'libraries': {name: any(name in k for k in dependencies) for name in ('retrofit', 'okhttp', 'coil', 'glide', 'timber', 'hilt')},
            'limitations': limitations}
