# PyPI Publish Guide

Releases are triggered manually from a tag ref. Nothing publishes automatically on push.

## Files

- [`.github/workflows/pypi-publish.yml`](https://github.com/kayentaconsulting/katalogue-python/blob/main/.github/workflows/pypi-publish.yml) — entry point
- [`.github/actions/pypi-publish-package/action.yml`](https://github.com/kayentaconsulting/katalogue-python/blob/main/.github/actions/pypi-publish-package/action.yml) — composite action that builds and publishes one package

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

The entry workflow runs two jobs in order:

```
validate-tag → publish
```

The `publish` job publishes both packages in sequence — `katalogue-sdk` first, then
`katalogue-cli`, because the CLI depends on the SDK. Each package is handled by the
`pypi-publish-package` composite action, which:

1. Builds the package with `uv build`
2. Uploads to the target registry based on `mode`

The job checks out the repo with full history (`fetch-depth: 0`), required for
`hatch-vcs` version derivation.

## Versioning

Both packages derive their version from the git tag at the repo root via `hatch-vcs`. The version embedded in the built wheel matches the tag exactly — no manual version bumps needed.

## Environment Protection

The `pypi` and `test-pypi` GitHub Environments gate the upload steps. Configure required reviewers in **Settings → Environments** to restrict who can approve a publish.
