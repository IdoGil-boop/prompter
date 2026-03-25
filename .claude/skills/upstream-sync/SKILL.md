<!-- managed by claude-code-starter -->
# Upstream Sync — Push Learnings to Starter

Push a universal lesson, gotcha, or improvement discovered in this project back to the `claude-code-starter` origin repo, so every future project (and every `--sync`) benefits.

## When to Use

- A gotcha was discovered that applies to **any** project (not just this one)
- A rule, agent, skill, or hook was improved in a way that's stack-agnostic
- A new best practice emerged that should be the default for all projects

## Workflow

### 1. Classify the Learning

Ask: "Would this help someone starting a brand-new project?"
- **YES** → Continue (upstream it)
- **NO** (project-specific) → Add to a `-local` file or project memory instead. STOP.

### 2. Determine the Target

| Learning type | Target file in `.claude-starter/` |
|--------------|----------------------------------|
| Gotcha / pitfall | `base/docs/reference/COMMON_GOTCHAS.md` |
| Coding rule | `base/.claude/rules/{relevant-rule}.md` |
| Agent improvement | `base/.claude/agents/{agent}.md` |
| Skill improvement | `base/.claude/skills/{skill}/SKILL.md` |
| Hook improvement | `base/.claude/hooks/{hook}.py` |
| New skill | `base/.claude/skills/{new-skill}/SKILL.md` + update `INDEX.md` |
| Command improvement | `base/.claude/commands/{cmd}.md` |
| Install script fix | `install.sh` |

### 3. Apply the Change

```bash
# The starter clone lives at .claude-starter/ in the project root
cd .claude-starter

# Pull latest first to avoid conflicts
git pull --rebase origin main

# Make the edit (Claude does this via Edit tool)
# ...

# Commit with a clear message
git add -A
git commit -m "<type>: <what was learned>

Discovered in <project_name>. Applies universally because <reason>.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# Push upstream
git push origin main

cd ..
```

### 4. Re-sync This Project

After pushing upstream, re-sync so the local `.claude/` copy matches:

```bash
.claude-starter/install.sh --sync
```

This overwrites managed files with the updated versions (including the change you just pushed).

## Rules

1. **Never upstream project-specific content** — no company names, custom endpoints, proprietary logic
2. **Use template variables** (`{{VAR_NAME}}`) for anything project-dependent
3. **Keep the managed header** — every file pushed upstream must have `<!-- managed by claude-code-starter -->` (or the pack variant `<!-- managed by claude-code-starter [pack:name] -->`)
4. **Pull before push** — always `git pull --rebase` in `.claude-starter/` first
5. **One concern per commit** — don't bundle unrelated fixes
6. **Test locally** — verify `install.sh --sync` still works after your change

## Gotcha Categories (for COMMON_GOTCHAS.md)

When adding to `COMMON_GOTCHAS.md`, place under the correct section:
- **ORM / Database** — SQLAlchemy, migration, query pitfalls
- **Infrastructure** — Docker, CI, deployment, SSL, environment
- **Frontend** — React, Next.js, build tools, CSS
- **Testing** — pytest, fixtures, mocking, flaky tests
- **API / Integration** — External APIs, auth, serialization

Format each entry as:
```markdown
### Short Title
**Symptom**: What goes wrong
**Cause**: Why it happens
**Fix**: How to solve it
```

## Definition of Done

- [ ] Change pushed to `claude-code-starter` origin (`git log` in `.claude-starter/` shows the commit)
- [ ] `install.sh --sync` runs clean after the push
- [ ] No project-specific content leaked upstream
- [ ] Commit message references the originating project context
