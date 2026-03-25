<!-- managed by claude-code-starter -->
# Skills Maintenance (Session-Aware)

Update Claude Code skills in `.claude/skills/` based on what was learned or built during this session.

## Workflow

1. **Review what happened this session:**
   - What patterns or conventions were established?
   - Were any existing skills used? Did they need adjustment?
   - Did the session involve a repeatable multi-step process?
2. **Update existing skills if needed**
3. **Propose new skills if warranted** (present, don't auto-create)
4. **Update `.claude/skills/INDEX.md`** if skills were added or modified

## Skill Type Taxonomy

| Type | Example | Complexity | Key Sections |
|------|---------|-----------|--------------|
| **Reference** | `frontend-patterns`, `coding-standards` | Light | Topics + code examples + tables |
| **Checklist** | `commit-by-feature`, `verify-plan` | Medium | When to Use + Step-by-step + Rules |
| **Session-aware** | `skills-maintenance`, `memory-curation` | Medium | Reviews session context + proposes changes |
| **Process loop** | `iterative-retrieval` | Medium | Cycle diagram + stop conditions |
| **Enforced workflow** | `debug-workflow` | Heavy | Task DAG + Router Contracts + CONTRACT RULEs + self-healing + memory layer |

When creating a new skill, identify which archetype fits. For enforced workflows, use `create-cc10x-flow` as the template.

## Rules

- Skills live in `.claude/skills/<skill-name>/SKILL.md`
- Prefer updating existing skills over creating new ones
- One purpose per skill — split if outgrown
- Keep SKILL.md concise (<100 lines)
- Don't create a skill for a one-off task

## Definition of Done

- Existing skills affected by session changes are updated
- `.claude/skills/INDEX.md` reflects current state
- Any new skill proposals are presented (not auto-created)
