from pathlib import Path
import re
import yaml
import json
from jsonschema import Draft202012Validator
from ..errors import StackError
from ..utils import safe_path

DATA = Path(__file__).resolve().parents[1] / 'data'


def load_recipe(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text())
        schema = json.loads((DATA/'recipe.schema.json').read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: str(e.path))
        if errors:
            raise ValueError('; '.join(f"{'.'.join(map(str,e.path)) or 'recipe'}: {e.message}" for e in errors))
        required = {'id': str, 'name': str, 'version': str, 'category': str,
                    'description': str, 'source': dict, 'requirements': dict,
                    'dependencies': list, 'features': list, 'variables': dict,
                    'files': list, 'integration': dict, 'validation': list}
        if not isinstance(data, dict):
            raise ValueError('Expected a mapping')
        for key, kind in required.items():
            if key not in data or not isinstance(data[key], kind):
                raise ValueError(f'{key}: expected {kind.__name__}')
        if not re.fullmatch(r'[a-z][a-z0-9-]*', data['id']):
            raise ValueError('Invalid recipe id')
        if not re.fullmatch(r'\d+\.\d+\.\d+', data['version']):
            raise ValueError('Invalid recipe version')
        if data['category'] not in ('project', 'network', 'image', 'logging'):
            raise ValueError('Invalid category')
        for key in ('repository', 'revision', 'license'):
            if not isinstance(data['source'].get(key), str) or not data['source'][key]:
                raise ValueError(f'source.{key} is required')
        for dep in data['dependencies']:
            if not isinstance(dep, dict) or not all(isinstance(dep.get(k), str) and dep[k] for k in ('module', 'version', 'configuration')):
                raise ValueError('Invalid dependency')
            if not re.fullmatch(r'[\w.-]+:[\w.-]+', dep['module']):
                raise ValueError('Invalid dependency module')
            if dep['configuration'] not in ('implementation', 'testImplementation'):
                raise ValueError('Unsupported dependency configuration')
        for file in data['files']:
            if not isinstance(file, dict) or not all(isinstance(file.get(k), str) for k in ('template', 'path')):
                raise ValueError('Invalid file declaration')
            if not safe_path(path.parent, file['template']).is_file():
                raise ValueError(f"Missing template: {file['template']}")
            if '..' in Path(file['path']).parts or Path(file['path']).is_absolute():
                raise ValueError('Unsafe output path')
        data['_root'] = path.parent
        return data
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        raise StackError(f'Invalid recipe {path}: {exc}') from exc


def recipes() -> dict[str, dict]:
    result = {}
    for path in sorted(DATA.glob('recipes/*/*/recipe.yaml')):
        recipe = load_recipe(path)
        if recipe['id'] in result:
            raise StackError(f"Duplicate recipe: {recipe['id']}")
        result[recipe['id']] = recipe
    return result


def get_recipe(name: str) -> dict:
    try:
        return recipes()[name]
    except KeyError as exc:
        raise StackError(f'Unknown recipe: {name}') from exc
