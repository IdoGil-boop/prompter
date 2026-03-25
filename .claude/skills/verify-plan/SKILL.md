<!-- managed by claude-code-starter -->
---
name: verify-plan
description: Verifies a plan document was fully executed by cross-checking each phase/item against actual code. Use after implementation to confirm nothing was missed.
---

# Plan Verification

Systematic code-level audit of a plan document against the actual codebase.

## When to Use

- After a multi-agent implementation session before creating a PR
- When an agent reports "COMPLETE" but you want independent verification
- When handing off between sessions

## Workflow

### Step 1 — Read the Plan
Extract each phase/sub-item as a checklist. Identify file, behavior, required/optional.

### Step 2 — Check Each Item Against Code
- File existence checks (`ls path/to/file`)
- Content verification (`grep` for specific patterns)
- Type/compile checks
- Test pass verification

### Step 3 — Produce Assessment Table

| Phase | Item | Status | Evidence |
|-------|------|--------|----------|
| 1A | Feature X in file.py | ✅ VERIFIED | `file.py:10` |
| 2B | Security check | ❌ MISSING | Not found |

Status codes:
- ✅ VERIFIED — code confirms it
- ⏭️ SKIPPED — plan marked optional
- ⚠️ NOT VERIFIABLE — requires manual check
- ❌ MISSING — required but not found

### Step 4 — Flag Gaps
Look for: deleted files that should exist, type mismatches, created but unwired code, tests that don't cover claimed scenarios.

### Step 5 — Git Status
```bash
git status --short
git log --oneline -10
```

Unstaged changes = work done but not saved. Flag prominently.
