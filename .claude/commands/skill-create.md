<!-- managed by claude-code-starter -->
---
description: Analyze git history to extract coding patterns and generate SKILL.md files
---

# Skill Create

Analyze recent git history and session context to extract a new skill.

## Steps

1. Review `git log --oneline -20` for patterns
2. Identify the repeatable pattern
3. Create `.claude/skills/<skill-name>/SKILL.md` with:
   - Name and description
   - When to use
   - Step-by-step workflow
   - Rules and constraints
   - Definition of done
4. Update `.claude/skills/INDEX.md`

## Skill Template

```markdown
---
name: skill-name
description: One-line description
---

# Skill Name

## When to Use
- Trigger conditions

## Workflow
1. Step one
2. Step two

## Rules
- Constraint one

## Definition of Done
- Completion criteria
```
