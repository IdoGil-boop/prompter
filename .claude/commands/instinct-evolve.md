<!-- managed by claude-code-starter -->
---
description: Cluster related instincts (3+) into skills, commands, or agents
---

# Instinct Evolve

When 3+ related instincts accumulate in a domain, cluster them into higher-level artifacts.

## Steps

1. Read all instincts, group by domain
2. For each domain with 3+ instincts:
   - Analyze common triggers and actions
   - Determine if they form a **skill** (auto-triggered), **command** (user-invoked), or **agent** (multi-step)
3. Propose the evolved artifact
4. If approved, create in `.claude/instincts/evolved/{agents,skills,commands}/`
5. Link back to source instincts via `evolved_from` field

## Rules

- Only propose, never auto-create
- Source instincts are preserved (not deleted)
- Evolved artifacts link back to sources
