<!-- managed by claude-code-starter -->
# cc10x Mobile Audit Patch (Post-Update)

Inject the mobile-auditor, ux-ui-advisor, and security-privacy-advisor agents into the cc10x-router's BUILD workflow as conditional steps. Follows the same surgical-edit pattern as `cc10x-codex-patch`.

## When to Run

- The cc10x plugin was updated (BUILD workflows no longer include conditional agents)
- A new session starts and frontend BUILD workflows aren't running mobile-audit/ux/security
- The router file was reset or recreated
- After running `/cc10x-codex-patch` (apply this patch after codex patch)

## Workflow

### Step 1: Find the current router file

```bash
find ~/.claude/plugins/cache/cc10x -name "SKILL.md" -path "*/cc10x-router/*" 2>/dev/null
```

Store the path as `$ROUTER_FILE`.

### Step 2: Verify patch is needed

Check if mobile-audit is already present:
```bash
grep -c "mobile-audit" "$ROUTER_FILE"
```
If count > 0, the patch is already applied — stop here.

### Step 3: Apply edits

**Edit 1 — Agent Chains table:** Add conditional agents to the BUILD chain.

Find the BUILD row in the Decision Tree table. Add `[mobile-auditor? ∥ ux-ui-advisor? ∥ security-privacy-advisor?]` between reviewers and integration-verifier. The `?` suffix indicates conditional steps.

**Edit 2 — BUILD parent task description:** Update the chain description to include the conditional agents.

**Edit 3 — BUILD Workflow Tasks:** Add three TaskCreate blocks for mobile-auditor, ux-ui-advisor, and security-privacy-advisor. Set their blockedBy to the reviewer tasks, and update integration-verifier to be blocked by all three.

```
TaskCreate({
  subject: "CC10X mobile-auditor: Audit mobile compatibility",
  description: "Conditional: runs ONLY if changed files include frontend/ paths.\nAssess via: git diff --name-only HEAD~1 HEAD | grep -c '^frontend/' \nIf count > 0: spawn mobile-auditor agent on all pages/components.\nIf count = 0: skip and mark completed immediately.\nWrites report to docs/qa/MOBILE_AUDIT.md.",
  activeForm: "Auditing mobile compatibility"
})

TaskCreate({
  subject: "CC10X ux-ui-advisor: Review UX/UI quality",
  description: "Conditional: runs ONLY if changed files include frontend/ paths OR user request mentions UI/UX/design/usability.\nAssess via: git diff --name-only HEAD~1 HEAD | grep -cE '^frontend/|\\.(tsx|jsx|css|scss|html)$' \nIf count > 0 OR request contains UI/UX keywords: spawn ux-ui-advisor agent.\nIf count = 0 AND no UI/UX keywords: skip and mark completed immediately.",
  activeForm: "Reviewing UX/UI quality"
})

TaskCreate({
  subject: "CC10X security-privacy-advisor: Review security & privacy",
  description: "Conditional: runs ONLY if changed files touch security-sensitive paths OR user request mentions security/privacy/auth.\nAssess via: git diff --name-only HEAD~1 HEAD | grep -cE 'auth|security|crypto|payment|token|permission|secret|password|session|middleware|api/|routes/' \nIf count > 0 OR request contains security/privacy keywords: spawn security-privacy-advisor agent.\nIf count = 0 AND no security keywords: skip and mark completed immediately.",
  activeForm: "Reviewing security & privacy"
})
```

All three are blocked by `[reviewer_task_id, hunter_task_id]`. Integration-verifier is blocked by all three.

**Edit 4 — Execution sections:** Add execution sections for each agent after the review phase.

**CRITICAL:** All diff commands MUST use `git diff --name-only HEAD~1 HEAD` (not `HEAD` alone). The component-builder commits changes before these agents run, so `HEAD` alone sees an empty working tree. `HEAD~1 HEAD` compares the last commit against its parent, capturing exactly what was changed.

Each execution section follows this pattern:
```
1. Run the diff check: git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -c '<pattern>' || echo 0
2. If "0" (and no keyword match for ux/security): skip → TaskUpdate completed
3. If > 0 (or keyword match): spawn the agent via Task(subagent_type="general-purpose")
4. Parse output for CRITICAL/HIGH/MEDIUM/LOW findings
5. Feed findings to integration-verifier
```

**Edit 5 — Execution Depth Selector:** If present, also fix `git diff --name-only HEAD` references in the pre-check and condition checks to use `HEAD~1 HEAD`.

### Step 4: Verify the patch

```bash
grep -c "mobile-audit" "$ROUTER_FILE"   # Expected: 4+
grep -c "ux-ui-advisor" "$ROUTER_FILE"  # Expected: 4+
grep -c "security-privacy" "$ROUTER_FILE"  # Expected: 4+
grep -c "HEAD~1 HEAD" "$ROUTER_FILE"    # Expected: 8+ (all diff commands use HEAD~1)
```

## Rules

- **Idempotent** — check before applying; don't double-patch
- **Order-aware** — apply AFTER cc10x-codex-patch if both are needed
- **Version-aware** — the router structure may change across cc10x versions; if old_string anchors don't match, read the file and adapt
- **Don't modify other workflows** — only patch BUILD; DEBUG/REVIEW/PLAN stay unchanged
- **Preserve formatting** — match the existing indentation and style in the router file
- **Always use HEAD~1 HEAD** — never use bare `HEAD` in diff commands (see COMMON_GOTCHAS.md: "Agent Workflow Diff Gates See Empty Diffs After Commit")

## Prerequisites

These project files must exist (they are version-controlled and survive plugin updates):
- `.claude/agents/mobile-auditor.md` — mobile compatibility audit agent
- `.claude/agents/ux-ui-advisor.md` — UX/UI review agent (CandleKeep-backed)
- `.claude/agents/security-privacy-advisor.md` — security & privacy review agent (CandleKeep-backed)
- `.claude/skills/mobile-audit/SKILL.md` — standalone mobile audit skill

## Definition of Done

- Router file contains all edits for all three conditional agents
- All `git diff` commands in the router use `HEAD~1 HEAD` (not bare `HEAD`)
- Next BUILD workflow with frontend changes creates conditional agent tasks
- Next BUILD workflow WITHOUT relevant changes skips agents (auto-completed)
