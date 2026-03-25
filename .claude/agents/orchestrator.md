<!-- managed by claude-code-starter -->
---
name: orchestrator
description: "Lists available custom agents and recommends when to use each."
tools:
  - Read
  - Glob
maxTurns: 5
---

# Agent Orchestrator

Overview of custom agents available in this repository.

## Available Agents

| Agent | File | When to Use |
|-------|------|-------------|
| **planner** | `.claude/agents/planner.md` | New features, complex changes, unclear requirements |
| **architect** | `.claude/agents/architect.md` | System design, scalability, schema changes |
| **tdd-guide** | `.claude/agents/tdd-guide.md` | Test-driven development: RED-GREEN-REFACTOR |
| **code-reviewer** | `.claude/agents/code-reviewer.md` | After writing code; quality, security, patterns |
| **security-reviewer** | `.claude/agents/security-reviewer.md` | Auth changes, input handling, secrets management |
| **refactor-cleaner** | `.claude/agents/refactor-cleaner.md` | Dead code cleanup, duplicate consolidation |
| **post-session-maintainer** | `.claude/agents/post-session-maintainer.md` | End of session: docs, skills, memory, recommendations |
| **mobile-auditor** | `.claude/agents/mobile-auditor.md` | Mobile compatibility audit: touch targets, responsive layout, forms, tables |

## Available Skills

See [`.claude/skills/INDEX.md`](../skills/INDEX.md) for all project-scoped skills.

## Quick Reference

- **Post-session maintenance:** `/maintain`
- **Development workflows:** Use cc10x router if enabled
- **See all skills:** Read `.claude/skills/INDEX.md`
