# Prepare the CLI

For a Recipe operation, first resolve a trusted `android-stack` executable. Run `capabilities --json` by absolute path and compare the protocol, required capabilities and exact Recipe versions with `cli-requirements.json`. Additional capabilities are allowed. The nonempty runtime version must equal the installed distribution version. Reuse a compatible executable and keep its absolute path for the workflow.

## Install from GitHub development source

If no compatible CLI is available, propose installing the tested development commit `34d418039574bf04b0db74f80c9696c7a7db053c` from the canonical repository. Present the exact source, Python 3.11 executable, new absolute venv path outside the Android project, and installation effects. This uses Git and pip network access to fetch the pinned source and resolve Python build and runtime dependencies. The commit pins the project source. pip resolves dependencies within the package's declared constraints. The installation leaves the existing CLI, global PATH and Android project files intact.

Wait for explicit approval before creating the environment or running pip. If approval is declined or unavailable, stop before any project write. Use a fresh path and run the commands from outside the Android project. For POSIX shells, substitute the approved absolute path in the example below.

```sh
CLI_ENV=/absolute/path/to/new-venv
test ! -e "$CLI_ENV" && test ! -L "$CLI_ENV" &&
  python3.11 -m venv "$CLI_ENV" &&
  "$CLI_ENV/bin/python" -m pip --isolated install \
    'git+https://github.com/smallmarker/android-stack-skills.git@34d418039574bf04b0db74f80c9696c7a7db053c' &&
  "$CLI_ENV/bin/android-stack" capabilities --json
```

On Windows, use the approved Python 3.11 executable and the venv's `Scripts\python.exe` and `Scripts\android-stack.exe`, with the same Git URL and a fresh path. After installation, compare the capability report with the Skill contract before running any Recipe. Stop on installation failure, invalid JSON or a contract mismatch. Keep the old CLI available for rollback.

## Advanced offline RC bundle

This Skill ships with Android Stack Skills **0.3.0rc1**. The preparation artifacts are `android_stack_skills-0.3.0rc1-py3-none-any.whl`, the platform lock under `locks/`, `install_rc.py` and `release-manifest.json`. Use an approved local bundle whose capability report contains the exact Recipe version in the contract. Earlier bundles containing retrofit-standard 0.1.1 or 0.2.0 cannot prepare a 0.3.0 installation. After publication, use the confirmed GitHub Release for tag `v0.3.0rc1` in the project's canonical repository. This local candidate has no verified public URL. Obtain the expected manifest SHA-256 from a trusted release record or directly from the user. Never infer trust from checksums delivered only by the same untrusted source.

If a compatible isolated CLI exists, reuse it. Otherwise identify CPython 3.11, the supported platform, artifact source, exact version, manifest checksum, dependency lock and new environment path. Ask the user to approve the installation before running it. Declined or unavailable approval ends preparation before any project write. Keep the existing CLI available for rollback.

After approval, verify the installer script against the trusted manifest before executing it. Run the verified script from outside the Android project:

```sh
python3.11 -I /path/to/release/install_rc.py --manifest /path/to/release/release-manifest.json --sha256 EXPECTED_MANIFEST_SHA256 --venv /absolute/path/to/new-venv
```

The installer uses the bundled platform wheelhouse offline. An alternative local wheelhouse can be specified with `--wheelhouse` and must satisfy the same hashes. Use the returned absolute CLI path and recheck `capabilities --json` against this Skill before invoking any Recipe. Stop on failure. Avoid editable installs, PYTHONPATH overrides, floating versions, remote shell scripts and global upgrades.
