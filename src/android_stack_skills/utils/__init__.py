import hashlib
from pathlib import Path
from ..errors import StackError


def digest(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise StackError(f"Unsafe path: {relative}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise StackError(f"Path escapes project: {relative}")
    for parent in [candidate, *candidate.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise StackError(f"Symlink is not writable: {parent}")
    return candidate


def read_text(path: Path) -> str:
    with path.open(encoding='utf-8', newline='') as source:
        return source.read()


def module_path(project: Path, module: str, relative: str) -> Path:
    path = Path(relative)
    if not path.is_relative_to(module) or path == Path(module):
        raise StackError(f'Output path must be inside module {module}: {relative}')
    return safe_path(safe_path(project, module), str(path.relative_to(module)))
