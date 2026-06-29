# Troubleshooting

Common errors and how to resolve them. The CLI and SDK raise the same underlying
errors; the CLI maps them to [exit codes](../cli/commands.md#exit-codes) and stderr
messages.

## Contents

- [Configuration errors](#configuration-errors)
- [Authentication errors](#authentication-errors)
- [API errors](#api-errors)
- [Keychain issues](#keychain-issues)
- [Usage errors](#usage-errors)
- [Seeing what's happening](#seeing-whats-happening)

## Configuration errors

> `No client ID provided. Set KATALOGUE_CLIENT_ID or pass --client-id.`
> `No client secret provided ...` / `No base URL provided ...`

A required setting is missing. Resolution order is **flag/argument > environment
variable > config file > default**. Fix by one of:

- `katalogue auth login` (CLI) to store credentials, then `katalogue auth status` to confirm
- Set `KATALOGUE_CLIENT_ID`, `KATALOGUE_CLIENT_SECRET`, `KATALOGUE_URL`
- Pass `resolve_settings(client_id=..., client_secret=..., base_url=...)` (SDK)

> `Invalid URL: ... — must start with http:// or https://`

`KATALOGUE_URL` / `--base-url` must be a full URL including the scheme.

In the SDK these surface as `ConfigError` at client/Settings construction time.

## Authentication errors

> `Authentication failed: ...` (CLI) / `AuthError` (SDK) — HTTP 401

The credentials were rejected. Check that:

- The client ID and secret are correct and not expired/revoked
- The OAuth2 client has the required scopes (the client derives `system.read`,
  `datasource.read`, etc. from the resource) — see
  [Granting access to Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue)
- `KATALOGUE_TOKEN_URL` points at the right token endpoint (defaults to
  `<base-url>/oidc/token`)

The token is cached and refreshed automatically on expiry; you do not manage it.

## API errors

> `Error: ...` (CLI) / `ApiError` (SDK) — HTTP 4xx/5xx other than 401

The request reached the API but failed — e.g. a resource ID that doesn't exist, or a
server-side error. Verify the ID and resource, and re-run with `--verbose` to see
request details.

## Keychain issues

> `No keyring backend is available on this system.`
> `No stored credentials found in keyring. Run 'katalogue auth login' or set KATALOGUE_CLIENT_SECRET.`

The CLI stores the client secret in your OS keychain via
[keyring](https://pypi.org/project/keyring/). On headless servers or CI there may be
no backend. In that case, skip `auth login` and provide the secret through
`KATALOGUE_CLIENT_SECRET` instead.

The non-secret config (client ID, base URL, token URL) lives in your OS user config
directory — e.g. `~/.config/katalogue/config.toml` on Linux. `katalogue auth logout`
clears the token cache and removes the keychain entry.

## Usage errors

> Exit code `2`, or `table format cannot be combined with --template / file output options`

A CLI argument combination is invalid. Notably:

- `--format table` cannot be combined with `--template` or any file-output option
  (`--output-file`, `--split-by`, etc.) — choose `json`, `yaml`, or `csv`
- `--output-file` cannot be combined with `--split-by`
- `--split-by` writes to `--output-dir` and requires fetching children

See [Output formats](../cli/output-formats.md) for valid combinations.

## Seeing what's happening

Add `--verbose` / `-v` to print HTTP request details to stderr:

```bash
katalogue -v system list
```

In the SDK, catch the typed exceptions to inspect failures — see
[Error handling](../sdk/client.md#error-handling).
