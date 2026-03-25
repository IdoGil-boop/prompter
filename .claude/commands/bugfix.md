<!-- managed by claude-code-starter -->
---
description: Structured debugging workflow with cc10x-compatible task DAG enforcement
---

# Bugfix

Launch the structured debug workflow for a bug or issue.

> **ENFORCEMENT**: This workflow uses task dependencies (`addBlockedBy`) to prevent step skipping.
> Downstream tasks are physically blocked until upstream tasks complete.
> Each phase outputs a Router Contract YAML that is validated by CONTRACT RULEs.
> Failures trigger self-healing (REM-FIX tasks) with a circuit breaker at 3 active attempts.

## Step 1: Create Task DAG

Create ALL tasks upfront with dependencies. This is the structural enforcement — no phase can run out of order.

```
knowledge_search → reproduce → isolate → root_cause → hypothesize → fix → pattern_sweep ─┐
                                                    └→ test_writer (background) ───────────┤
                                                                                           → verify → document
```

## Step 2: Execute Chain

For each task in dependency order:

1. **Check runnable**: `TaskList()` → find tasks where status=pending AND all blockedBy are completed
2. **Set in_progress**: `TaskUpdate(task, status: "in_progress")`
3. **Execute phase**: Follow the phase instructions from the `debug-workflow` skill
4. **Output Router Contract**: Print the structured YAML contract for this phase
5. **Validate CONTRACT RULE**: Check contract outputs against rules. If violated → override STATUS to FAIL
6. **If PASS**: `TaskUpdate(task, status: "completed")` → next task unblocks
7. **If FAIL + self-healing applies**: Create REM-FIX task, block current task, resolve, then re-execute

## Step 3: Parallel Execution

After Phase 3 (root cause), two tasks unblock simultaneously:
- `test_writer_task` → spawns `debug-test-writer` agent **in background**
- `hypothesize_task` → continues in main context

Phase 6 (verify) is blocked by BOTH — it waits for the fix AND the parallel tests.

## Step 4: Self-Healing (Phase 6)

If verification fails:
1. Create `REM-FIX` task describing what failed
2. Block `verify_task` on `REM-FIX` task
3. Fix the issue
4. Mark `REM-FIX` complete → `verify_task` unblocks → re-verify
5. **Circuit breaker**: If 3+ active REM-FIX tasks → `AskUserQuestion` to user

## Step 5: Document (MANDATORY — inline, never delegated)

After verification passes:
- **Always** append to `docs/debug-history.md`
- Add gotcha to `docs/gotchas.md` if bug was counter-intuitive
- Consider creating debugging instinct

> **The workflow is complete when `document_task` reaches status `completed`.**
> The DAG guarantees every prior phase completed successfully.
