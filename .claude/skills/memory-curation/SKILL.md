<!-- managed by claude-code-starter -->
# Memory Curation (Session-Aware)

Capture durable knowledge from this session into CLAUDE.md and project memory.

## Workflow

1. **Review the session for durable learnings:**
   - **Decisions**: "We chose X over Y because Z"
   - **Conventions**: "From now on, always do X"
   - **Sources of truth**: "This function is the single authority for X"
   - **Gotchas**: "This broke because of X, watch out for Y"
2. **Classify each learning:**
   - Belongs in `CLAUDE.md`? → Update appropriate section
   - Belongs in `docs/`? → Update the doc, link from `CLAUDE.md`
   - Transient? → Skip
3. **Prune stale entries** if session work invalidated existing memory
4. **Keep `CLAUDE.md` short** — under 250 lines; extract detail into docs

## What Belongs in CLAUDE.md

- Source-of-truth declarations
- Coding conventions and anti-patterns
- Architecture decision summaries

## What Does NOT Belong

- What was done this session (session log, not memory)
- Temporary workarounds
- Implementation details (link to docs)

## Definition of Done

- Session learnings captured for future sessions
- CLAUDE.md under 250 lines, no stale references
- No duplication between CLAUDE.md and docs/
