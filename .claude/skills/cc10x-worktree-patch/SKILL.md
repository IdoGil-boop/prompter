<!-- managed by claude-code-starter -->
# cc10x Worktree Isolation Patch (Post-Update)

Inject worktree isolation as a DAG-enforced gate in cc10x-router BUILD and DEBUG workflows. Every code-changing workflow runs in a dedicated git worktree so in-progress work never pollutes the main branch.

## When to Run

- The cc10x plugin was updated (BUILD/DEBUG no longer enter worktrees)
- A new session starts and BUILD/DEBUG workflows aren't using worktrees
- The router file was reset or recreated
- After running `/cc10x-codex-patch` and `/cc10x-mobile-audit-patch`

## Workflow

### Step 1: Find the router file
```bash
find ~/.claude/plugins/cache/cc10x -name "SKILL.md" -path "*/cc10x-router/*" 2>/dev/null
```
Store as `$ROUTER_FILE`.

### Step 2: Check if patch is needed
```bash
grep -c "worktree-isolation" "$ROUTER_FILE"
```
If count > 0, already patched — stop.

### Step 3: Apply patches

#### Patch W1: Worktree Isolation section (before Task-Based Orchestration)

In the router file, find `## Task-Based Orchestration` and insert this section **before** it. Includes:
- `<!-- worktree-isolation -->` marker
- Size assessment table (LARGE = auto-enter, SMALL = ask-for-name)
- Already-in-worktree detection
- **Router Contract** with STATUS, WORKTREE_NAME, WORKTREE_PATH, SIZE_ASSESSMENT, ALREADY_IN_WORKTREE
- **CONTRACT RULEs:**
  ```
  STATUS=ENTERED but WORKTREE_PATH is empty
    → Override: STATUS=FAILED, BLOCKING=true,
      REMEDIATION_REASON="EnterWorktree called but no path returned."

  STATUS=FAILED
    → BLOCKING=true. Do NOT proceed to task hierarchy.
      → AskUserQuestion: "Retry EnterWorktree / Abort workflow"
  ```
- No auto-exit — user merges via `/merge-worktrees`

#### Patch W2: BUILD Task DAG — add worktree_task

In `### BUILD Workflow Tasks`, after parent workflow TaskCreate, add:

```
TaskCreate({
  subject: "CC10X worktree: Enter isolated worktree",
  description: "**ROUTER: Execute inline — NEVER spawn Agent().**\n\nEnter isolated worktree. Validate Router Contract: STATUS=ENTERED|ALREADY_IN_WORKTREE.",
  activeForm: "Entering worktree"
})
# Returns worktree_task_id
```

Then block `builder_task_id` on `worktree_task_id`:
```
TaskUpdate({ taskId: builder_task_id, addBlockedBy: [worktree_task_id] })
```

Update parent task chain description to include `worktree →` prefix.

#### Patch W3: DEBUG Task DAG — add worktree_task

In `### DEBUG Workflow Tasks`, after parent workflow TaskCreate, add the same worktree task. Block `investigator_task_id` on `worktree_task_id`:
```
TaskUpdate({ taskId: investigator_task_id, addBlockedBy: [worktree_task_id] })
```

Update parent task chain description to include `worktree →` prefix.

#### Patch W4: Chain Execution Loop — add worktree gate guard

In the Chain Execution Loop step 2 (start agents), before the "Document-debug guard", add:

```
- **Worktree gate guard:** If task subject starts with "CC10X worktree:":
  → Execute INLINE. NEVER spawn Agent().
  → Follow Worktree Isolation section: check if already in worktree, assess size, call EnterWorktree.
  → Validate Router Contract: STATUS must be ENTERED or ALREADY_IN_WORKTREE.
  → If STATUS=FAILED: AskUserQuestion "Retry / Abort". Do NOT mark completed until resolved.
  → TaskUpdate({ taskId, status: "completed" }).
  → Continue to next runnable task.
```

#### Patch W5: BUILD workflow execution — update step 1b

In `### BUILD` execution section, update step 1b to reference the DAG task:

```
1b. **Worktree isolation** — executes inline via `worktree_task` (see Worktree Isolation section):
    - `worktree_task` is in the DAG — `builder_task_id` is blocked by it
    - Assess task size, enter worktree
    - Validate Router Contract: STATUS must be ENTERED or ALREADY_IN_WORKTREE
    - If FAILED → AskUserQuestion: "Retry / Abort"
    - `TaskUpdate(worktree_task_id, status: "completed")` — unblocks builder
```

#### Patch W6: DEBUG workflow execution — update step 1a

Same as W5 but for DEBUG, referencing `investigator_task_id`.

#### Patch W7: Planning-patterns — add worktree context to plans

In the `planning-patterns` skill file, add to the Plan Document Header template:

```markdown
**Worktree:** All BUILD phases execute in an isolated git worktree. The plan does not need to manage branching — the cc10x-router handles worktree entry/exit automatically. Use `/merge-worktrees` after implementation to merge back.
```

### Step 4: Verify
```bash
grep -c "worktree-isolation" "$ROUTER_FILE"          # Expected: 1+
grep -c "EnterWorktree" "$ROUTER_FILE"                # Expected: 3+
grep -c "merge-worktrees" "$ROUTER_FILE"              # Expected: 1+
grep -c "CC10X worktree:" "$ROUTER_FILE"              # Expected: 4+ (task creates + guards)
grep -c "worktree_task_id" "$ROUTER_FILE"             # Expected: 4+ (creates + blockedBy)
grep -c "Worktree gate guard" "$ROUTER_FILE"          # Expected: 1 (chain execution)
```

## Rules

- **Idempotent** — check before applying
- **Order-aware** — apply AFTER codex-patch and mobile-audit-patch
- **Version-aware** — adapt if router structure changed
- **BUILD + DEBUG only** — PLAN and REVIEW are exempt
- **DAG-enforced** — worktree_task blocks the first agent; no agent can run without passing the gate
- **CONTRACT RULE validated** — STATUS=ENTERED or ALREADY_IN_WORKTREE required; FAILED blocks all progress
- **Never skip worktree** — both LARGE and SMALL enter worktree; only the UX differs (auto vs ask-for-name)
- **No auto-exit** — user controls merge/cleanup via `/merge-worktrees`

## Prerequisites

- `EnterWorktree` tool available in Claude Code session
- `.claude/skills/merge-worktrees/SKILL.md` — the merge skill for cleanup

## Definition of Done

- Router file contains worktree isolation section with `<!-- worktree-isolation -->` marker
- BUILD Task DAG includes `worktree_task_id` blocking `builder_task_id`
- DEBUG Task DAG includes `worktree_task_id` blocking `investigator_task_id`
- Chain Execution Loop has worktree gate guard (inline execution)
- Router Contract + CONTRACT RULEs validate worktree entry
- `planning-patterns` header includes worktree note
- Next BUILD/DEBUG workflow physically cannot run agents until worktree gate passes
