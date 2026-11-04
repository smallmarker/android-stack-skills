"""Inspect a bounded subset of Android Kotlin DSL source-set declarations."""
from pathlib import Path
import re

from ..errors import StackError
from ..utils import safe_path

TOKEN = re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_]\w*|[^\s]')
SET = re.compile(r'getByName\s*\(\s*"(main|test)"\s*\)\s*\{([^{}]*)\}\s*;?')
DIRS = re.compile(r'\s*java\s*\.\s*setSrcDirs\s*\(\s*listOf\s*\(\s*("[\w./-]+"(?:\s*,\s*"[\w./-]+")*)\s*,?\s*\)\s*\)\s*;?\s*')
UNSUPPORTED = 'Cannot resolve sourceSets. Supported syntax is literal Android main/test java.setSrcDirs(listOf(...)).'


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN.findall(text) if not token.startswith(('//', '/*'))]


def declared_roots(text: str) -> dict[str, list[str]]:
    parts = tokens(text)
    layout = {}
    stack = []
    for i, token in enumerate(parts):
        if token == '{':
            stack.append(parts[i-1] if i else '')
        elif token == '}' and stack:
            stack.pop()
        elif token == 'sourceSets':
            if stack != ['android'] or parts[i-1] == '.':
                raise StackError(UNSUPPORTED)
            tail = ' '.join(parts[i+1:])
            block = re.match(r'^\{ ((?:[^{}]|\{[^{}]*\})*)\}', tail)
            if block:
                body = block[1].strip()
                rest = tail[block.end():]
                declarations = []
                while body:
                    item = SET.match(body)
                    if not item:
                        raise StackError(UNSUPPORTED)
                    declarations.append(item)
                    body = body[item.end():].strip()
            else:
                item = SET.match(tail.removeprefix('. ').strip())
                if not item or not tail.startswith('. '):
                    raise StackError(UNSUPPORTED)
                declarations = [item]
                rest = tail.removeprefix('. ').strip()[item.end():]
            if rest.lstrip().startswith(('.', '?', '[', '(')):
                raise StackError(UNSUPPORTED)
            for item in declarations:
                dirs = DIRS.fullmatch(item[2])
                if not dirs or item[1] in layout:
                    raise StackError(UNSUPPORTED)
                layout[item[1]] = re.findall(r'"([^"]+)"', dirs[1])
    return layout


def inspect_layout(base: Path, text: str, root_text: str, package: str) -> dict:
    try:
        if 'sourceSets' in tokens(root_text) or re.search(r'\bapply\s*(?:\(\s*from\s*=|\{\s*from\s*\()', ' '.join(tokens(text + '\n' + root_text))):
            raise StackError('Cannot resolve source roots configured in root or applied Gradle scripts.')
        configured = declared_roots(text)
        sets = {}
        for source_set in ('main', 'test'):
            conventional = [f'src/{source_set}/java', f'src/{source_set}/kotlin']
            declared = configured.get(source_set, [])
            roots = []
            for name in dict.fromkeys(declared + [r for r in conventional if not declared or r.endswith('/kotlin')]):
                root = safe_path(base, name)
                if root == base or (root.exists() and not root.is_dir()):
                    raise StackError(f'Invalid {source_set} source directory: {name}')
                package_dir = safe_path(root, package.replace('.', '/')) if root.is_dir() else None
                roots.append({
                    'path': name, 'exists': root.is_dir(), 'declared': name in declared,
                    'package_exists': package_dir is not None and package_dir.is_dir(),
                    'kotlin_files': sum(file.is_file() and not file.is_symlink() for file in root.rglob('*.kt')),
                })
            sets[source_set] = roots
        main = {safe_path(base, root['path']) for root in sets['main']}
        test = {safe_path(base, root['path']) for root in sets['test']}
        if any(a.is_relative_to(b) or b.is_relative_to(a) for a in main for b in test):
            raise StackError('Main and test source roots overlap.')
        return {'main': sets['main'], 'test': sets['test'], 'issue': None}
    except StackError as exc:
        return {'main': [], 'test': [], 'issue': str(exc)}


def choose_source_root(roots: list[dict], source_set: str, default: str) -> str:
    declared = [root for root in roots if root['declared']]
    candidates = declared or [root for root in roots if root['exists']]
    if not candidates:
        return default
    packages = [root for root in candidates if root['package_exists']]
    candidates = packages or candidates
    maximum = max(root['kotlin_files'] for root in candidates)
    best = [root['path'] for root in candidates if root['kotlin_files'] == maximum]
    if len(best) == 1:
        return best[0]
    raise StackError(f'Ambiguous {source_set} source roots ({", ".join(best)}). Use a single explicit sourceSets root or clarify the directory convention.')
