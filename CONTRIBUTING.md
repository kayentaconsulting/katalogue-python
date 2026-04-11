# Contributing to Katalogue CLI & SDK

Thanks for your interest in contributing to Katalogue CLI & SDK!

We welcome bug fixes, features, and documentation improvements.

## Getting the Source Code

Clone or fork this repository. You will need [uv](https://docs.astral.sh/uv/) and OAuth2 client credentials for a Katalogue instance.

## Setting Up a Local Development Environment

Set the following environment variables, or put them in a `.env` file at the repo root:

```bash
KATALOGUE_CLIENT_ID=your-client-id
KATALOGUE_CLIENT_SECRET=your-client-secret
KATALOGUE_URL=https://your-instance.katalogue.se
```

Then install all workspace dependencies:

```bash
uv sync
```

## Making Changes

Here is the basic process with all important steps to have in mind when making changes.

1. Get the source code and set up the development environment as described above.
1. Write tests for your change first (RED), then implement until they pass (GREEN). We do not accept untested code.
1. Make your changes.
1. If applicable, update the documentation.
1. If applicable, update the changelog in `/CHANGELOG.md`.
1. Run the full quality gate before submitting:
    ```bash
    uv run ruff check --fix && uv run ruff format
    uv run pytest -q
    ```
1. Submit a pull request with your changes when you are done, see below.

### Development Guidelines

- Keep changes focused and small.
- Follow existing code style and patterns.
- Pull requests must be production-ready. Half-finished features will not be accepted.
- `katalogue-sdk` must not depend on Click — keep it that way.
- Use Pydantic `BaseModel` for all data models; `SecretStr` for secrets.

## Submitting a Pull Request

1. Create a new branch for each feature on the form `<TYPE>/<ISSUE_NUMBER>_<SHORT_DESCRIPTION>`. Examples: `feat/123_add_glossary_list`, `fix/456_fix_auth_error_message`
1. Create a pull request that targets the `main` branch.
    - Clearly describe what you changed and why.
    - Link related issues if applicable.
1. CI must pass (ruff, pyright, pytest) before the pull request will be reviewed.
1. When a Katalogue code owner has reviewed and approved your pull request, it will be merged to the `main` branch.
1. Delete the feature branch when it has been accepted and merged.
