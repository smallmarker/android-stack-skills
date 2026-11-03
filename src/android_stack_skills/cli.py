"""CLI output is JSON with --json, otherwise concise human-readable reports."""
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .errors import StackError


def emit(value: dict | list, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, default=str))
    elif isinstance(value, dict) and 'files' in value:
        print(f"Recipe: {value['recipe']} {value['version']}")
        print('Already installed:', value['already_installed'])
        for conflict in value['conflicts']:
            print('CONFLICT:', conflict)
        print('Adaptation:', json.dumps(value['adaptation'], ensure_ascii=False))
        for dependency in value['dependencies']:
            print(f"ADD {dependency['configuration']}: {dependency['module']}:{dependency['version']}")
        for risk in value['risks']:
            print('RISK:', risk)
        for file in value['files']:
            print(file['diff'])
        print('Verification:', ', '.join(value['validation']))
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(prog='android-stack')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('version')
    listing = commands.add_parser('recipes').add_subparsers(dest='action', required=True).add_parser('list')
    listing.add_argument('--json', action='store_true')
    for name in ('inspect', 'plan', 'install', 'verify', 'status', 'recover'):
        command = commands.add_parser(name)
        command.add_argument('--project', type=Path, required=True)
        command.add_argument('--module')
        command.add_argument('--json', action='store_true')
        if name in ('plan', 'install'):
            command.add_argument('--recipe', required=True)
        if name == 'install':
            command.add_argument('--dry-run', action='store_true')
            command.add_argument('--verify', action='store_true', help='Run real Gradle build/tests after installation')
    create = commands.add_parser('create')
    create.add_argument('--name', required=True)
    create.add_argument('--package', required=True)
    create.add_argument('--preset', choices=['lightweight', 'standard'], default='lightweight')
    create.add_argument('--ui', choices=['compose', 'xml'], default='compose')
    create.add_argument('--image', choices=['coil', 'glide'], help='Defaults to Coil for Compose and Glide for XML')
    create.add_argument('--output', required=True, type=Path)
    create.add_argument('--skip-verify', action='store_true', help='Generate only; reports unverified')
    create.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        from .manifest import recipes
        from .inspector import inspect
        from .resolver import plan
        from .installer import apply, status, recover
        from .validator import verify
        if args.command == 'version':
            print(__version__)
            return 0
        if args.command == 'recipes':
            result = [{'id': r['id'], 'version': r['version'], 'category': r['category']} for r in recipes().values()]
        elif args.command == 'inspect':
            result = inspect(args.project, args.module)
        elif args.command in ('plan', 'install'):
            result = plan(args.project, args.recipe, args.module)
            if args.command == 'install' and not args.dry_run:
                result = apply(result)
                if args.verify:
                    result['verification'] = verify(args.project, args.module)
                    if not result['verification']['success']:
                        emit(result, args.json)
                        return 1
            elif result['conflicts']:
                emit(result, args.json)
                return 2
        elif args.command == 'verify':
            result = verify(args.project, args.module)
            emit(result, args.json)
            return 0 if result['success'] else 1
        elif args.command == 'status':
            result = status(args.project.resolve())
        elif args.command == 'recover':
            result = recover(args.project)
        else:
            from .generator import create_project
            result = create_project(args.name, args.package, args.preset, args.output, not args.skip_verify, ui=args.ui, image=args.image)
            emit(result, args.json)
            return 0 if result.get('verification', {}).get('success', args.skip_verify) else 1
        emit(result, args.json)
        return 0
    except (StackError, OSError, ValueError) as exc:
        if getattr(args, 'json', False):
            print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
