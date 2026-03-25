<!-- managed by claude-code-starter -->
# Workflow Recommender (Session-Aware)

Recommend new skills, agents, hooks, or commands to reduce friction in future sessions.

## When to Recommend

- Repeated manual steps
- Friction points (tasks that took too long)
- Missing automation
- Pattern emergence
- Toolbox gaps

## Workflow

1. **Review the session** for repetition and friction
2. **Classify each candidate:**
   - **Skill** — repeatable knowledge/checklist
   - **Agent** — multi-step workflow needing tool access
   - **Hook** — automatic trigger on events
   - **Command** — shortcut for common action
3. **Output recommendations** (present for user approval)

## Recommendation Format

```
### Recommendation: <short title>

**Type:** skill | agent | hook | command
**Why:** <what happened this session that motivates this>
**Where:** <file path where it would live>
**Effort:** low | medium | high
```

## Rules

- Only recommend if the pattern is likely to recur
- Don't duplicate existing skills/agents/hooks
- Present recommendations, don't auto-create
