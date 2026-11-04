# Prepare the CLI

Resolve the trusted `android-stack` executable and run `capabilities --json` using its absolute path. Check the protocol, required capabilities and Recipe versions in `cli-requirements.json`. Additional capabilities are allowed. The nonempty runtime version must equal the installed distribution version. Keep using the same executable. Missing commands, bad JSON or unmet requirements stop the workflow.

This Skill ships with Android Stack Skills **0.3.0rc1**. The preparation artifacts are `android_stack_skills-0.3.0rc1-py3-none-any.whl`, the platform lock under `locks/`, `install_rc.py` and `release-manifest.json`. Use the matching approved local RC bundle. After publication, use the confirmed GitHub Release for tag `v0.3.0rc1` in the project's canonical repository. This local candidate has no verified public URL. Obtain the expected manifest SHA-256 from a trusted release record or directly from the user. Never infer trust from checksums delivered only by the same untrusted source.

If a compatible isolated CLI exists, reuse it. Otherwise identify CPython 3.11, the supported platform, artifact source, exact version, manifest checksum, dependency lock and new environment path. Ask the user to approve the installation before running it. Declined or unavailable approval ends preparation before any project write. Keep the existing CLI available for rollback.

After approval, verify the installer script against the trusted manifest before executing it. Run the verified script from outside the Android project:

```sh
python3.11 -I /path/to/release/install_rc.py --manifest /path/to/release/release-manifest.json --sha256 EXPECTED_MANIFEST_SHA256 --venv /absolute/path/to/new-venv
```

The installer uses the bundled platform wheelhouse offline. An alternative local wheelhouse can be specified with `--wheelhouse` and must satisfy the same hashes. Use the returned absolute CLI path and recheck `capabilities --json` against this Skill before invoking any Recipe. Stop on failure. Avoid editable installs, PYTHONPATH overrides, floating versions, remote shell scripts and global upgrades.
