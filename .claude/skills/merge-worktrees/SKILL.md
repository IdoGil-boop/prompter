<!-- managed by claude-code-starter -->
---
name: merge-worktrees
description: Merge worktree branches back to the main branch and clean up. Uses Task DAG + CONTRACT RULEs to enforce commit-before-merge and diff-before-remove gates.
user_invocable: true
---

# Merge Worktrees

Merge completed work from git worktrees back to the main branch, then clean up.

> **ENFORCEMENT MODEL**: Same four-layer enforcement as cc10x BUILD/DEBUG flows:
> 1. **Structural** — Task DAG with `addBlockedBy` prevents out-of-order execution
> 2. **Contractual** — Router Contract YAML validates each phase's outputs
> 3. **Self-healing** — Failures create REM-FIX tasks that block progress until resolved
> 4. **Documentation** — Key decisions persisted to `.claude/cc10x/activeContext.md`

## Iron Laws

```
1. EVERY WORKTREE MUST HAVE ALL CHANGES COMMITTED BEFORE ANY MERGE BEGINS.
2. EVERY WORKTREE BRANCH DIFF FROM MAIN MUST BE REVIEWED BEFORE ANY WORKTREE IS REMOVED.
```

These are **hard requirements** — enforced by CONTRACT RULEs that block progress. No shortcut, no skip, no "I'll do it later."

---

## Task DAG (Dependency Graph)

Create all tasks at workflow start. Downstream tasks are **physically blocked** until their dependencies complete.

```
TaskCreate: survey_task         ← "CC10X MERGE: Survey Worktrees"
TaskCreate: commit_gate_task    ← "CC10X MERGE: Commit Gate (HARD REQUIREMENT)"
TaskCreate: select_task         ← "CC10X MERGE: Select Worktree"
TaskCreate: pre_merge_task      ← "CC10X MERGE: Pre-Merge Checks"
TaskCreate: merge_task          ← "CC10X MERGE: Execute Merge"
TaskCreate: restore_stash_task  ← "CC10X MERGE: Restore Stash"
TaskCreate: verify_task         ← "CC10X MERGE: Post-Merge Verify"
TaskCreate: diff_gate_task      ← "CC10X MERGE: Diff Review Gate (HARD REQUIREMENT)"
TaskCreate: cleanup_task        ← "CC10X MERGE: Clean Up Worktree"

# Dependencies (addBlockedBy):
commit_gate_task   ← blocked by: [survey_task]
select_task        ← blocked by: [commit_gate_task]
pre_merge_task     ← blocked by: [select_task]
merge_task         ← blocked by: [pre_merge_task]
restore_stash_task ← blocked by: [merge_task]
verify_task        ← blocked by: [restore_stash_task]
diff_gate_task     ← blocked by: [verify_task]
cleanup_task       ← blocked by: [diff_gate_task]
```

**Critical property**: All `addBlockedBy` calls are forward-only. The DAG has no cycles. A task CANNOT transition to `in_progress` until ALL its blockers have `completed` status.

---

## Phase 0: Survey Worktrees

**Task**: `survey_task`
**Blocked by**: nothing (entry point)

Detect context and enumerate all worktrees.

```bash
# Detect if we're in a worktree
git rev-parse --git-common-dir 2>/dev/null
git worktree list
```

Two modes:
- **In-worktree mode**: session is inside a worktree (entered via EnterWorktree)
- **Main-tree mode**: session is on the main branch with worktrees listed externally

For **every** worktree (not just the one being merged), collect:

```bash
git worktree list --porcelain
# For each worktree:
UNCOMMITTED=$(git -C <worktree_path> status -s | wc -l | tr -d ' ')
COMMITS_AHEAD=$(git log main..<branch> --oneline | wc -l | tr -d ' ')
```

Display:
| Worktree | Branch | Commits Ahead | Uncommitted Changes |
|----------|--------|---------------|---------------------|

If no worktrees exist (other than main), inform user and stop.

### Router Contract (Phase 0)
```yaml
PHASE: 0-survey
STATUS: COMPLETE
WORKTREE_COUNT: <count excluding main>
WORKTREES: ["<name1>:<branch1>:<commits_ahead>:<uncommitted>", ...]
IN_WORKTREE: true|false
```

### CONTRACT RULE
```
STATUS=COMPLETE but WORKTREE_COUNT=0
  → Override: STATUS=NOTHING_TO_MERGE,
    REMEDIATION_REASON="No worktrees found. Nothing to merge."
  → STOP workflow. Mark all tasks completed.
```

→ `TaskUpdate(survey_task, status: "completed")`

---

## Phase 1: Commit Gate (HARD REQUIREMENT)

**Task**: `commit_gate_task`
**Blocked by**: `[survey_task]`

**For EVERY worktree** (not just the merge target): check for uncommitted changes.

```bash
git -C <worktree_path> status -s
```

For EACH worktree where UNCOMMITTED > 0:
→ AskUserQuestion: "Worktree `{name}` has {N} uncommitted changes. These MUST be committed before merge can proceed."
  Options: "Commit all changes now" | "Show me the changes first" | "Abort merge"
→ "Show me the changes first":
    `git -C <worktree_path> diff`
    `git -C <worktree_path> diff --cached`
    → Then re-ask: "Commit these changes?" Options: "Commit all" | "Abort merge"
→ "Commit all changes now":
    `git -C <worktree_path> add -A`
    `git -C <worktree_path> commit -m "chore: commit uncommitted work before worktree merge`

    `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"`
→ "Abort merge": STOP workflow entirely.

**After processing all worktrees — re-verify:**
```bash
# Re-check EVERY worktree
git -C <worktree_path> status -s  # for each
```

### Router Contract (Phase 1)
```yaml
PHASE: 1-commit-gate
STATUS: ALL_CLEAN|HAS_UNCOMMITTED
WORKTREES_CHECKED: <count>
WORKTREES_COMMITTED: <count — those that needed commits>
UNCOMMITTED_REMAINING: <count — MUST be 0>
RECHECK_PERFORMED: true|false
```

### CONTRACT RULE
```
STATUS=ALL_CLEAN but UNCOMMITTED_REMAINING > 0
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Uncommitted changes remain in {worktree}. Cannot proceed to merge."

STATUS=ALL_CLEAN but RECHECK_PERFORMED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Post-commit re-verification not performed. Must re-check all worktrees."

WORKTREES_CHECKED < WORKTREE_COUNT (from Phase 0)
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Not all worktrees were checked. Gate applies to ALL worktrees, not just merge target."
```

**This gate applies to ALL worktrees, not just the merge target.** Rationale: uncommitted changes in *any* worktree could be lost if that worktree is later cleaned up or if branches interact.

→ `TaskUpdate(commit_gate_task, status: "completed")`

---

## Phase 2: Select Worktree

**Task**: `select_task`
**Blocked by**: `[commit_gate_task]`

**In-worktree mode (single):**
→ Default to current worktree. AskUserQuestion: "Merge current worktree `{name}` ({N} commits ahead) into main?"
  Options: "Merge and clean up" | "Merge and keep worktree" | "Abort"

**Main-tree mode (potentially multiple):**
→ AskUserQuestion: "Which worktree to merge?" with list of worktrees + status.

### Router Contract (Phase 2)
```yaml
PHASE: 2-select
STATUS: SELECTED
WORKTREE_NAME: "<name>"
WORKTREE_PATH: "<path>"
BRANCH: "<branch>"
COMMITS_AHEAD: <count>
KEEP_AFTER_MERGE: true|false
```

→ `TaskUpdate(select_task, status: "completed")`

---

## Phase 3: Pre-Merge Checks

**Task**: `pre_merge_task`
**Blocked by**: `[select_task]`

```bash
# 1. Ensure main is clean
git status -s
# If dirty: AskUserQuestion: "Main branch has uncommitted changes. Commit first / Stash / Abort"

# 2. Check for merge conflicts (dry run)
git merge --no-commit --no-ff <branch> 2>&1
git merge --abort  # always abort the dry run
# If conflicts: warn user with file list
```

### Router Contract (Phase 3)
```yaml
PHASE: 3-pre-merge
STATUS: READY|CONFLICTS_DETECTED|MAIN_DIRTY
MAIN_CLEAN: true|false
STASH_CREATED: true|false
CONFLICT_FILES: ["<path1>", ...] or []
DRY_RUN_PERFORMED: true|false
```

### CONTRACT RULE
```
STATUS=READY but MAIN_CLEAN ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Main branch has uncommitted changes. Must be clean before merge."

STATUS=READY but DRY_RUN_PERFORMED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Merge dry run not performed. Must check for conflicts before merging."
```

If CONFLICTS_DETECTED:
→ AskUserQuestion: "Merge conflicts detected in {N} files: {list}. How to proceed?"
  Options: "Resolve conflicts manually" | "Abort merge" | "Use theirs (worktree wins)" | "Use ours (main wins)"

→ `TaskUpdate(pre_merge_task, status: "completed")`

---

## Phase 4: Execute Merge

**Task**: `merge_task`
**Blocked by**: `[pre_merge_task]`

**Default strategy: merge commit** (preserves worktree history as a branch)

```bash
# If in worktree: exit first
ExitWorktree(action="keep")  # keep until merge verified

# On main branch:
git merge <branch> --no-ff -m "merge: cc10x-{workflow}-{description}

Worktree branch merged after cc10x {WORKFLOW} workflow.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

**Alternative strategies** (offer if user requests):
- **Squash**: `git merge --squash <branch>` — collapses all worktree commits into one
- **Rebase**: `git rebase main` (from worktree branch) then fast-forward merge — linear history

### Router Contract (Phase 4)
```yaml
PHASE: 4-merge
STATUS: MERGED|FAILED
STRATEGY: merge|squash|rebase
MERGE_COMMIT: "<sha>"
EXITED_WORKTREE: true|false|not_applicable
```

### CONTRACT RULE
```
STATUS=MERGED but MERGE_COMMIT is empty
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Merge commit SHA not captured. Verify merge actually occurred."
```

→ `TaskUpdate(merge_task, status: "completed")`

---

## Phase 4.5: Restore Stash

**Task**: `restore_stash_task`
**Blocked by**: `[merge_task]`

If Phase 3 stashed dirty main changes (`STASH_CREATED=true`), restore them now.

```bash
# Only if STASH_CREATED=true from Phase 3:
git stash pop
```

If `git stash pop` fails (conflict with merged changes):
→ AskUserQuestion: "Stash pop failed — the stashed changes conflict with the merge. How to proceed?"
  Options: "Drop the stash (discard pre-merge changes)" | "Keep stash for manual resolution" | "Abort"
→ "Drop the stash": `git stash drop`
→ "Keep stash for manual resolution": warn user stash remains at `git stash list` index 0
→ "Abort": STOP workflow.

If `STASH_CREATED=false` → mark completed immediately, skip restore.

### Router Contract (Phase 4.5)
```yaml
PHASE: 4.5-restore-stash
STATUS: RESTORED|SKIPPED|CONFLICT
STASH_CREATED: true|false
STASH_POPPED: true|false|not_applicable
STASH_DROPPED: true|false|not_applicable
```

### CONTRACT RULE
```
STATUS=RESTORED but STASH_POPPED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Stash was created in Phase 3 but not restored. Must pop or explicitly drop."

STASH_CREATED=true but STATUS=SKIPPED
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Phase 3 created a stash but Phase 4.5 skipped restore. Stashed changes will be lost."
```

→ `TaskUpdate(restore_stash_task, status: "completed")`

---

## Phase 5: Post-Merge Verify

**Task**: `verify_task`
**Blocked by**: `[restore_stash_task]`

```bash
git log --oneline -5            # confirm merge commit
git diff HEAD~1 --stat          # show what changed
```

Run project tests if available:
```bash
pytest 2>&1 | tail -20   # quick verification
```

### Router Contract (Phase 5)
```yaml
PHASE: 5-verify
STATUS: PASS|FAIL
MERGE_COMMIT_VISIBLE: true|false
FILES_CHANGED: <count>
TEST_EXIT: <exit code or "no_test_cmd">
```

### CONTRACT RULE
```
STATUS=PASS but MERGE_COMMIT_VISIBLE ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Merge commit not visible in git log. Verify merge succeeded."
```

### Self-Healing (Phase 5)
```
If STATUS=FAIL:
  1. TaskCreate: rem_fix_task ← "CC10X REM-FIX: Merge verification failed"
     description: "<what failed>"
  2. TaskUpdate(verify_task, addBlockedBy: [rem_fix_task])
  3. When rem_fix_task completes → re-run Phase 5 verification
```

→ `TaskUpdate(verify_task, status: "completed")`

---

## Phase 6: Diff Review Gate (HARD REQUIREMENT)

**Task**: `diff_gate_task`
**Blocked by**: `[verify_task]`

**Before removing ANY worktree**, display the full diff between the worktree branch and main.

```bash
# Show what the worktree branch had vs current main (post-merge)
git diff main..<branch> --stat
git diff main..<branch>
```

Present to user and get explicit confirmation:

→ AskUserQuestion: "Above is the diff between `{branch}` and main. All changes are accounted for. Remove worktree and branch?"
  Options: "Yes, remove worktree and branch" | "Keep worktree for now" | "Show full diff again"

→ "Show full diff again": re-display `git diff main..<branch>`, then re-ask.
→ "Keep worktree for now": skip removal. Set KEEP_WORKTREE=true. Proceed to completion.
→ "Yes, remove worktree and branch": set DIFF_REVIEWED=true.

### Router Contract (Phase 6)
```yaml
PHASE: 6-diff-gate
STATUS: REVIEWED|SKIPPED_KEEP
DIFF_DISPLAYED: true|false
DIFF_STAT_LINES: <count>
USER_CONFIRMED: true|false
KEEP_WORKTREE: true|false
```

### CONTRACT RULE
```
STATUS=REVIEWED but DIFF_DISPLAYED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Worktree branch diff from main was not displayed. MUST show diff before removing."

STATUS=REVIEWED but USER_CONFIRMED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="User did not explicitly confirm diff review. Must get confirmation before removing worktree."
```

→ `TaskUpdate(diff_gate_task, status: "completed")`

---

## Phase 7: Clean Up

**Task**: `cleanup_task`
**Blocked by**: `[diff_gate_task]`

**Only executes if KEEP_WORKTREE=false from Phase 6.**

If KEEP_WORKTREE=true → mark completed immediately, skip removal.

```bash
# Remove the worktree
git worktree remove <worktree_path>

# Delete the branch (already merged)
git branch -d <branch>
```

### Router Contract (Phase 7)
```yaml
PHASE: 7-cleanup
STATUS: REMOVED|KEPT|FAILED
WORKTREE_REMOVED: true|false
BRANCH_DELETED: true|false
```

### CONTRACT RULE
```
STATUS=REMOVED but WORKTREE_REMOVED ≠ true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="git worktree remove did not succeed."

STATUS=REMOVED but BRANCH_DELETED ≠ true
  → WARNING (not blocking): Branch may still exist. Verify with `git branch -a`.
```

→ `TaskUpdate(cleanup_task, status: "completed")`

After cleanup, check for remaining worktrees:
```bash
git worktree list
```
If more worktrees remain:
→ AskUserQuestion: "Merge another worktree?" with remaining list.
→ If yes: start a new merge workflow DAG from Phase 0 (commit gate re-runs for safety).

---

## Stale Worktree Cleanup

Even stale/abandoned worktrees MUST pass both hard requirement gates:
1. **Commit gate (Phase 1)**: if uncommitted changes exist, commit them first
2. **Diff gate (Phase 6)**: display `git diff main..<branch> --stat` and confirm with user

No exceptions — even if branch appears empty/merged.

## Quick Reference

| Phase | Task | Blocked By | Contract Key | Hard Requirement |
|-------|------|------------|-------------|-----------------|
| 0 | Survey | — | WORKTREE_COUNT | No |
| 1 | Commit Gate | Phase 0 | UNCOMMITTED_REMAINING=0, RECHECK=true | **YES** |
| 2 | Select | Phase 1 | WORKTREE_NAME, BRANCH | No |
| 3 | Pre-Merge | Phase 2 | MAIN_CLEAN, DRY_RUN, STASH_CREATED | No |
| 4 | Merge | Phase 3 | MERGE_COMMIT | No |
| 4.5 | Restore Stash | Phase 4 | STASH_POPPED | No |
| 5 | Verify | Phase 4.5 | MERGE_COMMIT_VISIBLE | Self-healing |
| 6 | Diff Gate | Phase 5 | DIFF_DISPLAYED, USER_CONFIRMED | **YES** |
| 7 | Cleanup | Phase 6 | WORKTREE_REMOVED | No |

> **Completion rule**: The workflow is NOT done until `cleanup_task` status is `completed`. The DAG enforces this — cleanup_task cannot complete until diff_gate_task completes, which cannot complete until verify_task completes, and so on back to survey_task.

## Rules

- **Never force-delete** — use `git branch -d` (not `-D`) to prevent deleting unmerged work
- **Never remove without diff review** — even if branch appears merged, show the diff
- **Never merge with uncommitted changes** — in ANY worktree, not just the target
- **Preserve history by default** — use `--no-ff` merge commits unless user requests squash/rebase
- **One at a time** — merge worktrees sequentially to avoid conflicts between them
- **Test after merge** — run project tests if test command is configured
