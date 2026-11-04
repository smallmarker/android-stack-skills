"""Stable capability report for independently distributed Skills."""
from importlib import metadata
from pathlib import Path
import sys

from . import __version__
from .manifest import recipes

PROTOCOL = 1
CAPABILITIES = (
    'workflow.plan-install-verify.v1',
    'plan.diagnostics.v1',
    'install.internet-permission.v1',
    'install.source-layout.v1',
    'network.kotlin-2.0.21-profile.v1',
    'inspect.image-libraries.v1',
    'create.ui-image.v1',
    'distribution.release-identity.v1',
)


def report() -> dict:
    try:
        distribution = metadata.version('android-stack-skills')
    except metadata.PackageNotFoundError:
        distribution = None
    return {
        'protocol': PROTOCOL,
        'version': __version__,
        'distribution_version': distribution,
        'python': sys.executable,
        'module': str(Path(__file__).resolve()),
        'capabilities': list(CAPABILITIES),
        'recipes': {name: recipe['version'] for name, recipe in recipes().items()},
    }
