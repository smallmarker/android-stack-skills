"""Prepare a minimal, validated INTERNET permission insertion."""

import re
import xml.etree.ElementTree as ET

ANDROID = 'http://schemas.android.com/apk/res/android'
TOOLS = 'http://schemas.android.com/tools'
INTERNET = 'android.permission.INTERNET'
ROOT_START = re.compile(
    r'\A\s*(?:(?:<\?xml[^?]*\?>|<!--.*?-->)\s*)*'
    r'<manifest(?=\s|>)(?:[^>"\']|"[^"]*"|\'[^\']*\')*>',
    re.DOTALL,
)


def internet_permission_edit(text: str) -> str | None:
    """Return an insertion for a normal manifest, or None if permission is present.

    Raise ValueError for forms that need a manual edit, including merge overrides.
    """
    root = ET.fromstring(text)
    if root.tag != 'manifest':
        raise ValueError('Expected a manifest root element')
    for child in root:
        if child.tag not in ('uses-permission', 'uses-permission-sdk-23', 'uses-permission-sdk-m'):
            continue
        if child.get(f'{{{ANDROID}}}name') != INTERNET:
            continue
        if (
            child.tag != 'uses-permission'
            or child.get(f'{{{ANDROID}}}maxSdkVersion') is not None
            or child.get(f'{{{TOOLS}}}node') is not None
            or child.get(f'{{{TOOLS}}}remove') is not None
        ):
            raise ValueError('Existing INTERNET permission has an SDK restriction or merge override')
        return None

    start = ROOT_START.match(text)
    if start is None or start[0].endswith('/>'):
        raise ValueError('Manifest root layout needs a manual permission insertion')
    declaration = ''
    if not re.search(r'\bxmlns:android\s*=\s*["\']'+re.escape(ANDROID)+r'["\']', start[0]):
        declaration = f' xmlns:android="{ANDROID}"'
    newline = '\r\n' if '\r\n' in text else '\n'
    insertion = f'{newline}    <uses-permission{declaration} android:name="{INTERNET}" />'
    if not text[start.end():].startswith(('\n', '\r')):
        insertion += newline
    updated = text[:start.end()] + insertion + text[start.end():]
    ET.fromstring(updated)
    return updated
