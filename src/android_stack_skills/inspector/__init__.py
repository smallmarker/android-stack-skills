"""Conservative inspection: unresolved values stay unknown."""
from pathlib import Path
import re
import tomllib
from ..errors import StackError
from ..utils import digest, read_text
from .source_layout import inspect_layout


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
    root_text = (project/'build.gradle.kts').read_text() if (project/'build.gradle.kts').exists() else ''
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
        text = read_text(build)
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
        layout = inspect_layout(base, text, root_text, namespace.group(1) if namespace else 'unknown')
        layout['build_sha256'] = digest(text)
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
                        'source_layout': layout,
                        'sources': [str(base.relative_to(project)/root['path']) for root in layout['main'] if root['exists']]})
    dependencies.update({k: v for m in modules for k, v in m['dependencies'].items()})
    chosen = [m for m in modules if module is None or m['name'] == ':'+module.strip(':')]
    module_text = (project/chosen[0]['build']).read_text() if len(chosen) == 1 else ''

    def plugin_version(*plugin_ids: str) -> str:
        for text in (module_text, root_text):
            # Keep quoted strings intact while skipping commented-out plugin declarations.
            text = re.sub(r'("(?:\\.|[^"\\])*")|/\*.*?\*/|//[^\n]*',
                          lambda match: match.group(1) or ' ', text, flags=re.DOTALL)
            for plugin_id in plugin_ids:
                invocation = r'id\(\s*"' + re.escape(plugin_id) + r'"\s*\)'
                if plugin_id == 'org.jetbrains.kotlin.android':
                    invocation = r'(?:' + invocation + r'|kotlin\(\s*"android"\s*\))'
                declared = re.search(invocation + r'\s+version\b(?:\s+"([^"]+)")?', text)
                if declared:
                    return declared.group(1) or 'unknown'
            for alias, entry in catalog.get('plugins', {}).items():
                accessor = alias.replace('-', '.').replace('_', '.')
                if not re.search(r'alias\(\s*libs\.plugins\.' + re.escape(accessor) + r'\s*\)', text):
                    continue
                if isinstance(entry, str):
                    plugin_id, _, version = entry.partition(':')
                else:
                    plugin_id = entry.get('id')
                    version = entry.get('version', 'unknown')
                    if isinstance(version, dict):
                        version = versions.get(version.get('ref'), 'unknown')
                if plugin_id in plugin_ids:
                    return version if isinstance(version, str) and version else 'unknown'
        return 'unknown'
    wrapper = project/'gradle/wrapper/gradle-wrapper.properties'
    wrapper_text = wrapper.read_text() if wrapper.exists() else ''
    urls = re.findall(r'^\s*distributionUrl\s*[=:]\s*(.+)$', wrapper_text, re.M)
    match = re.search(r'gradle-([\d.]+)-(?:bin|all)\.zip$', urls[0].strip()) if len(urls) == 1 else None
    limitations = []
    if 'projectDir' in settings.read_text() or 'includeBuild' in settings.read_text():
        limitations.append('Custom projectDir/includeBuild mappings require manual adaptation')
    if not modules:
        limitations.append('No literal Android module recognized; dynamic settings/custom plugin conventions require manual adaptation')
    if len(chosen) != 1:
        limitations.append('Select exactly one Android module with --module')
    return {'project': str(project), 'android': bool(modules), 'settings': settings.name,
            'catalog': str(catalog_file.relative_to(project)) if catalog_file.exists() else 'unknown',
            'kotlin': plugin_version('org.jetbrains.kotlin.android'),
            'agp': plugin_version('com.android.application', 'com.android.library'), 'gradle': match.group(1) if match else 'unknown',
            'wrapper': (project/'gradlew').is_file(), 'modules': modules,
            'selected': chosen[0] if len(chosen) == 1 else None,
            'libraries': {name: any(name in k for k in dependencies) for name in ('retrofit', 'okhttp', 'coil', 'glide', 'timber', 'hilt')},
            'limitations': limitations}
