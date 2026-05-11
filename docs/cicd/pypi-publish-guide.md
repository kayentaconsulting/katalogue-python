# PyPI Publish Guide

Releases are triggered manually from a tag ref. Nothing publishes automatically on push.

## Files

- [`.github/workflows/pypi-publish.yml`](../.github/workflows/pypi-publish.yml) — entry point
- [`.github/workflows/_pypi-publish-package.yml`](../.github/workflows/_pypi-publish-package.yml) — builds and publishes one package

## How to Release

1. Create and push a version tag:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

2. Go to **Actions → Publish to PyPI → Run workflow** in GitHub.

3. Select the tag ref from the **Branch** dropdown (switch from branch to tag).

4. Choose a mode:
   - `dry-run` — builds packages, no upload
   - `test-pypi` — publishes to [test.pypi.org](https://test.pypi.org)
   - `pypi` — publishes to [pypi.org](https://pypi.org)

5. Click **Run workflow**.

## Tag Format

The workflow validates the tag before building. Accepted formats:

| Format | Example |
|--------|---------|
| Release | `v1.2.3` |
| Alpha | `v1.2.3a1` |
| Beta | `v1.2.3b1` |
| Release candidate | `v1.2.3rc1` |
| Dev | `v1.2.3dev1` |

Running from a branch ref or a malformed tag will fail at the validation step before any build runs.

## Pipeline

The entry workflow runs three jobs in order:

```
validate-tag → publish-sdk → publish-cli
```

The SDK publishes before the CLI because `katalogue-cli` depends on `katalogue-sdk`.

Each package job is handled by the reusable workflow, which:

1. Checks out the repo with full history (required for `hatch-vcs` version derivation)
2. Sets up `uv`
3. Builds the package with `uv build`
4. Uploads to the target registry based on `mode`

## Versioning

Both packages derive their version from the git tag at the repo root via `hatch-vcs`. The version embedded in the built wheel matches the tag exactly — no manual version bumps needed.

## Environment Protection

The `pypi` and `test-pypi` GitHub Environments gate the upload steps. Configure required reviewers in **Settings → Environments** to restrict who can approve a publish.
