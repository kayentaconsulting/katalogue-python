---
title: Retrieval & export design
description: Why get() is one polymorphic method, how glossary-side exports differ, and the trade-offs behind each choice.
---

This page records the non-obvious design decisions behind catalog retrieval and
export, and the trade-offs that were weighed. It is aimed at maintainers changing
`client.get()`, the assemblers in `exporting.py`, or the CLI export commands.

## Layering recap

| Layer | File | Responsibility |
|-------|------|---------------|
| HTTP + routing | `packages/katalogue-sdk/src/katalogue/client/api.py` | One `get()` entry point, OAuth2, typed errors |
| Hierarchy assembly | `packages/katalogue-sdk/src/katalogue/exporting.py` | Build the flat canonical shape per resource |
| Output | `packages/katalogue-sdk/src/katalogue/output.py` | Render / write / split |
| CLI commands | `packages/katalogue-cli/src/katalogue_cli/cli/<resource>.py` | Parse args → `run_get()` → emit |

The CLI never makes HTTP calls and the SDK never imports `click`. Every decision
below pushes logic into the SDK so the CLI stays a thin wrapper and direct SDK
callers get the same guarantees.

## Decision 1 — One polymorphic `get()`, not per-strategy methods

`client.get(resource, options)` routes internally based on which options are set:

| Options | Route | Endpoint |
|---------|-------|----------|
| `resource_id` | single record | `/api/{resource}/{id}` |
| `parent_id` | children of a parent | `/api/{resource}/{parent_resource}/{id}` |
| `reference_parent_id` | many-to-many lookup | `/api/reference/get_by_to_id/...` |
| `include_children` | full hierarchy | assembler (see Decision 3) |
| none | all records | `/api/{resource}/all` |

**Trade-off.** A single method hides the endpoint/strategy choice from callers, so
the CLI command files are nearly identical and adding a resource rarely touches the
client. The cost is that `get()` carries the routing table (`_PARENT_RESOURCE`,
`_PARENT_ID_FIELD`) and a branchy dispatch. We accepted that concentration because
the alternative — honest per-strategy methods (`get_one`, `list_children`,
`list_by_reference`, …) — would leak endpoint shape into every caller and multiply
the CLI boilerplate the SDK exists to absorb.

## Decision 2 — Inverse-FK lookup uses a targeted endpoint, not a scan

The `field → field_description` link is a foreign key **on the child**
(`field.field_description_id`). Answering "which fields use this field description?"
is therefore an inverse lookup. The catalog exposes it directly:

```
GET /api/field/field_description/{id}   →  list_by_parent("field", "field_description", id)
```

Both reference assemblers (`assemble_field_description_references`,
`assemble_business_term_references`) use this. `business-term export` calls it once
per linked field description.

**Why not scan.** The original implementation pulled the entire `field` table via
`list_resource("field")` and filtered in Python — O(all fields) per export, and N
full-table downloads in the "datamart for terms A, B, C" loop. On the demo catalog
that is ~4,600 rows per call.

**Trade-off — N+1.** `business-term export` is now `1 (term) + 1 (references) + D`
calls, where D = linked field descriptions. For the common case (small D) this is a
large win. For a term linked to many descriptions it is more round-trips than one
bulk pull. D is small in practice, so no adaptive fallback was added; if a pathological
term ever appears, the fix is to switch to one bulk scan when D exceeds a threshold
(keep the targeted path for small D). This is deliberately deferred, not forgotten.

## Decision 3 — System-side vs glossary-side assembly are different shapes

`include_children` dispatches to one assembler per resource (`_get_hierarchical`).
Two families exist:

- **System-side** (`system`, `datasource`, `dataset_group`, `dataset`) — assembled
  from the bulk `/api/export/system/{id}` endpoint, then sliced. Produces the flat
  canonical shape with `datasources` / `dataset_groups` / `datasets` / `fields`
  collections.
- **Glossary-side** (`glossary`, `business_term`, `field_description`) — assembled
  from the glossary export endpoint plus reference lookups. Produces a
  term/description-rooted shape (`business_terms[]` tree, `field_descriptions[]`,
  nested `fields[]`) with **no** system-side collections. `glossary` specifically
  returns a recursive `business_terms` tree — see Decision 6.

This split is the root cause of Decision 4 — most output machinery assumes the
system-side shape.

## Decision 4 — Glossary-side exports reject templates, `--split-by`, and filters

Templates (`dbt-source`, `column-mapping`, …), `--split-by`, and the hierarchical
filter pruner all assume the system-side `datasets`/`fields` shape. Against a
glossary-side shape they would crash on undefined keys, split nothing, or silently
drop the filter. The SDK rejects all three for `_GLOSSARY_SIDE_RESOURCES`
(`api.py`), and the CLI export commands drop the `--template` flag entirely so the
three glossary-side resources behave identically.

**Trade-off — reject vs implement.** We chose to reject filters with a clear error
rather than implement pruning for `terms` / `field_descriptions` / nested `fields`.
Reasons: (1) silent-drop is the actual bug, and an explicit error fixes the harm
immediately; (2) no current use case needs glossary-side filtering; (3) the flat
`list --filter` path already covers filtering these resources without
`include_children`. Implementing the pruner is the documented escape hatch if a real
need appears.

**Source of truth.** Enforcement lives in the SDK so a direct
`client.get("business_term", ...)` call is protected too; the CLI flag removal is
just not offering a knob that cannot work.

## Decision 5 — No explicit pagination handling

List endpoints accept an `n` page parameter (default page size 50) where an absent
/ `undefined` value returns all rows. The client passes no `n`, relying on
"absent → all". This was verified empirically: `field list` returns ~4,600 rows in a
single call on the demo instance, not 50.

**Trade-off.** This keeps the client simple and is correct for the current API, but
it is an implicit dependency on server behavior. If the API ever changes the default
to paginate when `n` is absent, every `list_*` call would silently truncate. The
mitigation, when needed, is to pass `n=undefined` explicitly or loop pages with the
`append` parameter. Left out now to avoid speculative complexity.

## Decision 6 — Glossary export is a reconstructed tree, not a flat list

`assemble_glossary` (`exporting.py`) turns the endpoint's flat `assets` list into a
recursive `business_terms` tree via `_build_glossary_tree`. This is a client-side
reconstruction, and it rests on several **non-obvious assumptions about the endpoint's
`full_path` field** that are not spelled out in `openapi.json` — worth knowing before
touching this code:

- **Response wrapper.** The live endpoint returns `{"export": {"meta", "data"}}`, but
  `openapi.json` documents the body as `GlossaryExport = {meta, data}` with **no**
  `export` wrapper. `assemble_glossary` unwraps `export` *then* `data` defensively so
  it works either way. This mismatch was the original "empty export" bug — do not
  remove the `export` unwrap on the assumption the spec is authoritative.
- **Business-term identity.** A business term's `full_path` is its own full identity
  (ends with its own name, e.g. `Customer::Sales Order`), and is **empty/null** for
  top-level terms. So a term's identity key = `full_path` if non-empty else `name`.
  Non-empty `full_path` always has ≥2 `::` segments (top-level terms are empty), so a
  term's parent identity = `full_path` minus the last segment, and top-level terms
  resolve their parent via the `name` fallback.
- **Field-description attachment.** A field description's `full_path` is its **parent
  term's** identity path (it does *not* include the FD's own name). So an FD attaches
  to the term whose identity equals `fd["full_path"]`.
- **Many-to-many is real.** The same field description `id` appears as multiple
  `assets` rows with different `full_path` values (e.g. "List Price" under both
  `Product` and `Customer::Sales Order::List Price`). The tree duplicates it under
  each parent **by design** — this is correct, not a dedup bug. CSV emits one row per
  attachment for the same reason.
- **Orphan promotion.** Terms whose parent identity can't be resolved, and field
  descriptions whose `full_path` matches no term, are promoted to the root
  (`business_terms` / top-level `field_descriptions`) so nothing is silently dropped.
  On the demo catalog there are currently 0 orphans, but the promotion is the
  safety net if the endpoint's paths ever drift.
- **CSV flattening.** `_flatten_glossary_for_csv` (`formatters.py`) DFS-walks the tree
  to one row per asset, so CSV row count == asset count. The pattern mirrors
  `rendering.py::_build_fields_tree` (group-by-parent + recursive attach + orphan
  promotion); keep them consistent if either changes.

## Files

- `client/api.py` — `get()`, `_get_hierarchical()`, `_GLOSSARY_SIDE_RESOURCES`, routing maps
- `exporting.py` — `assemble_*` functions, `_build_glossary_tree`, the flat-shape slicers, the filter pruner
- `formatters.py` — `_flatten_glossary_for_csv` and the system-side CSV flattener
- `output.py` — `OutputPipeline`, `_VALID_SPLITS` (glossary-side entries are empty)
- `cli/business_term.py`, `cli/glossary.py`, `cli/field_description.py` — the three glossary-side command surfaces (kept identical)

## Related

- AI agents skill page (`docs/src/content/docs/ai-agents/skill.md`) documents the
  user-facing contract these decisions produce.
