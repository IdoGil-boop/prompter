<!-- managed by claude-code-starter -->
---
description: Extract reusable patterns from current session and save as learned skills
---

# Learn Command

Reviews the current session for reusable patterns and proposes new skills.

## Workflow

1. Review `git diff --name-only HEAD` and `git log --oneline -10`
2. Identify repeatable patterns, conventions, or workflows
3. Check `.claude/skills/INDEX.md` for existing skills
4. Propose new skills or updates to existing ones
5. Present recommendations — don't auto-create

## What Makes a Good Skill

- Repeatable (would apply to future sessions)
- Specific (clear trigger and action)
- Not a one-off task
