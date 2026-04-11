# Contributing

## Prerequisites

You need [uv](https://docs.astral.sh/uv/) and OAuth2 client credentials for a Katalogue instance.

```bash
export KATALOGUE_CLIENT_ID=your-client-id
export KATALOGUE_CLIENT_SECRET=your-client-secret
export KATALOGUE_URL=https://your-instance.katalogue.se
```

Or put them in a `.env` file at the repo root.

```bash
uv sync   # install all workspace deps
```

## Branch naming

| Prefix | Use |
|--------|-----|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Tooling, CI, deps |

## Workflow

1. Open or find an issue — all work should be linked to one.
2. Branch off `main`: `git checkout -b feat/your-feature`.
3. **Write tests first** (RED), then implement (GREEN). No exceptions.
4. Keep changes small and reviewable — one logical slice per PR.
5. Before pushing, run the full quality gate:

```bash
uv run ruff check --fix && uv run ruff format
uv run pytest -q
```

CI runs the same checks. PRs that fail CI will not be merged.

## Pull requests

- Title: short imperative (`add system list command`, `fix auth error message`)
- Body: fill in the PR template — what, why, linked issue, checklist
- One approving review required before merge
- Squash or rebase — no merge commits on `main`

## Code style

- Pydantic `BaseModel` for all data models — no plain `@dataclass`
- `SecretStr` for secrets, `field_validator` for validation
- `katalogue-sdk` has no Click dependency — keep it that way
- Errors go to stderr; exit 0 success, 1 API/user error, 2 usage error
