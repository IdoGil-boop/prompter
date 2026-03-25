<!-- managed by claude-code-starter -->
# Docs Maintenance (Session-Aware)

Update project documentation in `docs/` to reflect what changed during this session.

## Workflow

1. **Understand what changed this session:**
   - Run `git diff --name-only HEAD` and `git log --oneline -5`
   - Review session context for decisions and changes made
2. **For each significant change, check if docs need updating:**
   - Feature behavior changed? → Update relevant doc
   - New API endpoint? → Update API docs
   - Module removed/renamed? → Update references
   - New pattern established? → Add to architecture docs
3. **Feature docs — create or update:**
   - **New feature**: Create doc in `docs/architecture/` or `docs/guides/`
   - **Modified feature**: Find and update existing doc
   - **Skip**: Bug fixes, config tweaks, minor refactors
4. **Fix collateral damage:**
   - Broken links from file renames/moves
   - Contradictions between updated code and stale docs
5. **Update `docs/INDEX.md`** if docs were added or removed

## Rules

- **All docs live in `docs/`** — don't create doc files elsewhere
- **Prefer updating existing docs** over creating new ones
- **Focus on session changes** — don't do a full audit
- **`docs/INDEX.md` must stay accurate**
- **CLAUDE.md is an intro+index** — never inline detailed content; move to `docs/` and reference

## Definition of Done

- Docs affected by session changes are updated
- No contradictions between changed code and docs
- `docs/INDEX.md` is accurate
- CLAUDE.md remains a concise index (~120 lines)
