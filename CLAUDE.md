# prompter — Agent Guide

This file is the **entry point** for Claude agents. It provides essential context and points to detailed docs. **Always check referenced docs before making changes in unfamiliar areas.**

**Full documentation**: [`docs/INDEX.md`](docs/INDEX.md)

---

## Project Overview

Prompter applies Karpathy's autoresearch concept to LLM agent optimization. It iteratively optimizes an agent config (system prompts, tools, RAG, context, memory) against a user-provided test suite. Tech stack: Python.

---

## Single Source of Truth Principle

**CRITICAL**: For any critical decision or computation, there MUST be only ONE authoritative implementation.

| Decision | Source of Truth | Location |
|----------|----------------|----------|
| <!-- Add project-specific sources of truth here --> |

**When adding new logic**: Check if the decision already exists. If yes, delegate. If no, create + document here.

---

## Essential References (Read Before Coding)

### Architecture & Design
- **[Architecture](docs/architecture/)** — System design docs
- **[Implementation Plan](docs/plans/2026-03-24-prompter-implementation-plan.md)** — Phased build plan (MVP → full optimizer loop)

### Gotchas & Patterns
- **[Common Gotchas](docs/reference/COMMON_GOTCHAS.md)** — Known pitfalls and workarounds

### Testing
- Coverage: 80%+ for new code. TDD mandatory for security-critical code.

---

## Documentation Rules (Anti-Inflation)

1. **Prefer updating existing docs** over creating new ones
2. **Max one new doc per session**
3. **CLAUDE.md is an index** — keep concise, move details to `docs/`. Reference, don't inline.
4. **`docs/INDEX.md` must stay accurate** — update it when docs are added/removed

---

## Key Architecture Decisions

<!-- Add project-specific decisions as they're made -->

---

## Agents, Skills & Maintenance

| Tool | Purpose | Command |
|------|---------|---------|
| Planner | Implementation planning | /plan |
| TDD Guide | Test-driven development | /tdd |
| Code Review | Quality + security review | /code-review |
| Post-session | Capture learnings | /maintain |
| Verify Plan | Cross-check implementation | /verify-plan |

### /maintain Workflow

The `/maintain` command runs post-session to keep docs accurate. Key rules:
1. **CLAUDE.md is an intro+index** — never inline detailed content. Move to `docs/` and reference.
2. Update `docs/INDEX.md` when docs are added or removed.
3. Update referenced docs when code changes make them stale.

---

**When unsure**: `docs/INDEX.md` → `docs/architecture/` → `docs/reference/` → recent commits → `.claude/`
