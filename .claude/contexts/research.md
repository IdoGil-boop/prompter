<!-- managed by claude-code-starter -->
# Research Mode

Read-only exploration. Understand before changing.

## Workflow

1. Start with `CLAUDE.md` for project overview
2. Check `docs/INDEX.md` for detailed docs
3. Use `/architecture-map` to understand structure
4. Grep for patterns: `grep -rn "pattern" backend/app/`
5. Read tests for behavior documentation

## Key Entry Points

- `backend/app/` — Main application code
- `backend/tests/` — Tests (behavior docs)
- `docs/architecture/` — Design decisions
- `docs/reference/COMMON_GOTCHAS.md` — Known pitfalls

## Rules

- **Read first, change later** — understand existing patterns
- **Check source of truth** — see CLAUDE.md before modifying shared logic
- **Note findings** — capture gotchas for `/maintain`
