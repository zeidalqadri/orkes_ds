# Architecture Decision Records

ADRs use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

## Template

```md
# {Short title}

{1-3 sentences: context, decision, and why.}
```

That's it. An ADR can be a single paragraph. Value is in recording *that* a decision was made and *why*.

## When to create

All three must be true:
1. **Hard to reverse** — meaningful cost to change mind later
2. **Surprising without context** — future reader will wonder why
3. **Result of a real trade-off** — genuine alternatives existed

## Optional sections

- **Status** frontmatter: `proposed | accepted | deprecated | superseded by ADR-NNNN`
- **Considered Options** — when rejected alternatives worth remembering
- **Consequences** — when non-obvious downstream effects

## What qualifies

- Architectural shape (monorepo, event-sourced, etc.)
- Integration patterns between contexts
- Technology choices with lock-in (DB, message bus, auth provider)
- Boundary and scope decisions
- Deliberate deviations from the obvious path
- Constraints not visible in code
- Rejected alternatives when non-obvious
