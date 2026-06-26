# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `yaml_str` Jinja2 filter for safe YAML scalar encoding in custom templates — single-line strings render as plain scalars, multiline strings render as `|-` block scalars; pair with Jinja2's native `indent(n, first=False)` to position content at the correct column, including dynamic depth inside recursive loops

### Fixed

- Tolerant boolean comparison in filters — `true`/`false` now match both the JSON boolean form and any casing of the string form (`"true"`, `"True"`, `"TRUE"`) (#85)

## [0.1.0] - TBD

### Added
- `katalogue-sdk` — standalone Python HTTP client for the Katalogue Data Catalog API with OAuth2 client credentials support
- `katalogue-cli` — Click CLI wrapping the SDK with resource-first command structure
- Commands for all core resources: `system`, `datasource`, `dataset-group`, `dataset`, `field`, `glossary`
- `list` and `get` verbs for every resource, with parent-scoping flags (e.g. `--system`, `--datasource`)
- `--where key=value` filtering and `--fields` projection on list commands
- `--format json|table|compact` output modes; JSON when piped, table on TTY
- `katalogue auth login/logout/status` with token caching via system keyring
- Config file support (`~/.config/katalogue/config.toml`) for persisting base URL and client ID
- `katalogue export` command for bulk data export
- URL-encoding of user-supplied path segments to prevent path traversal
- Lazy auth resolution — credentials only required when an API call is made
- CI pipeline with ruff, pyright, and pytest
- PyPI publish workflow with dry-run, TestPyPI, and production modes
- VCS-based versioning via `hatch-vcs` — version derived from git tags

[Unreleased]: https://github.com/kayentaconsulting/katalogue-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kayentaconsulting/katalogue-python/releases/tag/v0.1.0
