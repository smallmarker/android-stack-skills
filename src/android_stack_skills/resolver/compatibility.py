"""Verified Retrofit toolchains and conservative gates for the other recipes."""

from packaging.version import InvalidVersion, Version

NETWORK_TOOLCHAINS = {
    ('2.0.21', '8.13.1', '8.14.3'),
    ('2.2.20', '8.13.1', '8.14.3'),
}
VERSION_KEYS = ('kotlin', 'agp', 'gradle')
REVIEW_VERSIONS = (
    'Keep the existing versions and validate this exact combination in an isolated project. '
    'Before any upgrade, review the impact on Kotlin plugins, AGP, the Gradle wrapper, SDK '
    'requirements and CI, and obtain explicit approval.'
)


def version_issue(info: dict, selected: dict, recipe_id: str) -> tuple[str, str, str] | None:
    versions = tuple(info[key] for key in VERSION_KEYS)
    kotlin, agp, gradle = versions
    try:
        parsed_agp = Version(agp) if agp != 'unknown' else None
        parsed_gradle = Version(gradle) if gradle != 'unknown' else None
        parsed_kotlin = Version(kotlin) if kotlin != 'unknown' else None
    except InvalidVersion:
        return 'unverified_versions', f'Cannot evaluate toolchain versions {versions}', REVIEW_VERSIONS

    if parsed_agp and parsed_agp.release[:2] == (8, 13) and parsed_gradle and parsed_gradle < Version('8.13'):
        return 'incompatible_versions', f'AGP {agp} requires Gradle 8.13 or newer (found {gradle})', REVIEW_VERSIONS
    if parsed_agp and parsed_agp.major >= 9:
        return 'incompatible_versions', 'AGP 9+ is outside the installer’s explicit Kotlin plugin support', REVIEW_VERSIONS

    if recipe_id == 'retrofit-standard':
        if 'unknown' in versions:
            missing = ', '.join(key for key in VERSION_KEYS if info[key] == 'unknown')
            return 'unverified_versions', f'Cannot establish the Retrofit toolchain ({missing} unresolved)', REVIEW_VERSIONS
        legacy_ui_or_di = kotlin == '2.0.21' and (selected['compose'] is True or selected['hilt'])
        if versions not in NETWORK_TOOLCHAINS or legacy_ui_or_di:
            return (
                'unverified_versions',
                f'Retrofit combination Kotlin {kotlin}, AGP {agp}, Gradle {gradle} '
                f'(Compose={selected["compose"]}, Hilt={selected["hilt"]}) has no matching build evidence',
                REVIEW_VERSIONS,
            )
    elif (parsed_kotlin and parsed_kotlin < Version('2.2.20')) or (parsed_agp and parsed_agp < Version('8.13.0')):
        return 'unverified_versions', f'Toolchain {versions} is outside this Recipe’s tested baseline', REVIEW_VERSIONS
    return None
