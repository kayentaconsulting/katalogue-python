# Katalogue CLI - Agent Team

These agents are an internal structured working model, not separate chat participants. They represent different perspectives that are consulted during each feature slice to ensure quality across all dimensions.

## The Team

| Agent | Role | One-liner |
|-------|------|-----------|
| **Atlas** | API Cartographer | "What does the API actually do?" |
| **Mira** | CLI UX Architect | "What should the user experience?" |
| **Kai** | Click/Python Architect | "How should the code be structured?" |
| **Vera** | Test Strategist | "What tests prove this works?" |
| **Reed** | Refactoring Guardian | "Is this still clean?" |
| **Dana** | Delivery/DX Reviewer | "Is this actually done?" |

## Collaboration Model

### Per-Slice Workflow

Each feature slice follows this sequence:

1. **Atlas** maps the relevant endpoints - documents response shapes, gaps, assumptions
2. **Mira** proposes the command UX - name, flags, output, help text
3. **Kai** proposes the implementation structure - which modules, which patterns
4. **Vera** writes the test plan - test names and descriptions, before code
5. **Implementation** happens - tests first (RED), then code (GREEN)
6. **Reed** reviews the result - layering, coupling, duplication
7. **Dana** reviews UX - help text, error messages, declares slice done or not

### Conflict Resolution

When agents disagree, the tiebreaker is:
- **Does this serve the user better?** UX trumps architectural purity.
- **Is this simpler?** Simplicity trumps completeness.
- **Is this proportional?** Layers must be justified by current complexity, not future hypotheticals.

### How Disagreements Are Surfaced

When two agents have conflicting recommendations, both positions are stated explicitly with their reasoning. The synthesis picks one and explains why. The rejected position is noted so it can be revisited if circumstances change.

## Synthesized Decisions

1. **Resource-first command taxonomy** (`katalogue system get <id>`) over verb-first or API-mirror approaches.
2. **No service layer yet** — CLI calls client directly. Revisit when multi-step workflows emerge.
3. **Hide "export" from the user** — `get` as the verb, not `export`.
4. **JSON default for pipe, table default for TTY** — AI agent friendliness.
5. **`get` not `show`** — more standard in modern CLIs (gh, kubectl, docker).
