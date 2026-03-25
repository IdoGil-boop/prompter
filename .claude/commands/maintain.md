<!-- managed by claude-code-starter -->
Run post-session maintenance: capture this session's learnings into the Claude toolbox.

> **IMPORTANT — commit & push rules**:
> - You MAY commit doc/skill/memory changes as part of this workflow.
> - You MUST NOT `git push` anything without explicit user approval.

First, understand what happened this session:
- Run `git diff --name-only HEAD` and `git log --oneline -5` to see what changed
- Review the conversation context for decisions, patterns, and gotchas

Then execute these phases using that session context:

1. **Docs** — Do the docs still match the code after this session's changes? Update any docs that describe changed behavior. Fix broken links from renames. Update `docs/INDEX.md` if needed.

2. **Feature Docs** — Did a feature get created or significantly modified?
   - **New feature**: Create a doc in `docs/architecture/` or `docs/guides/`. Name it after the feature.
   - **Modified feature**: Find the existing doc and update it.
   - **Skip**: Bug fixes, config tweaks, minor refactors.
   - Add to `docs/INDEX.md` and reference from `CLAUDE.md` if architecturally significant.

3. **Skills** — Did a repeatable pattern emerge? Update existing skills if outdated. Propose new skills only if a clear pattern crystallized (don't auto-create).

4. **Memory (CLAUDE.md + docs/)** — CLAUDE.md is an **intro + index**, not a detail dump.
   - **NEVER inline detailed content into CLAUDE.md**. Update the referenced doc instead.
   - CLAUDE.md should stay under ~120 lines.

5. **Recommendations** — What was tedious or repetitive? Suggest hooks, commands, skills, or agents (present, don't auto-create).

Load each skill from `.claude/skills/<name>/SKILL.md` for detailed guidance.

End with a summary of what changed, what was captured, and any recommendations.
