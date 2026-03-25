<!-- managed by claude-code-starter -->
# cc10x Router Patches (Post-Update)

Re-apply custom patches to the cc10x-router after a plugin update overwrites the cached router file.

## When to Run

- cc10x plugin was updated (BUILD workflows no longer include codex-review step, or DEBUG no longer includes bugfix phases)
- New session and codex-review tasks or bugfix phases aren't active
- Router file was reset or recreated

## Workflow

### Step 1: Find the router file
```bash
find ~/.claude/plugins/cache/cc10x -name "SKILL.md" -path "*/cc10x-router/*" 2>/dev/null
```

### Step 2: Check if patches are needed
```bash
grep -c "codex-review" "$ROUTER_FILE"   # BUILD patch
grep -c "bugfix-knowledge-search" "$ROUTER_FILE"  # DEBUG patch
```
If both > 0, already patched — stop.

### Step 3a: Apply BUILD patches (codex-review)
Adapt the edits to the current router file structure. Key patches:
1. Add `[codex-review]` to BUILD chain between reviewers and verifier
2. Add codex task to BUILD task hierarchy
3. Wire verifier dependency through codex task

### Step 3b: Apply DEBUG patches (bugfix workflow integration)
Inject the 7-phase debug-workflow methodology into the DEBUG flow. Key patches:

#### Patch D1: Knowledge search step
In the `### DEBUG` workflow section, **after** "Load memory → Check patterns.md Common Gotchas" (step 1), insert:

```
1.5. **Knowledge search (bugfix Phase 0):**
   - Read `docs/gotchas.md` — check if this bug matches a known gotcha
   - Read `docs/debug-history.md` — check if a similar bug was previously fixed
   - Search instincts: `Bash(command="grep -rl 'domain: debugging' .claude/instincts/ 2>/dev/null")`
   - If a match is found, pass as `## Known Issue Context` in bug-investigator prompt
   - If strong match (exact symptom): suggest applying known fix and skip to verification
   <!-- bugfix-knowledge-search -->
```

#### Patch D2: Cache cleanup step
In the `### DEBUG` workflow section, **after** the CLARIFY step (step 2), insert:

```
2.5. **Cache cleanup (bugfix pre-hook):**
   Bash(command="find . -maxdepth 3 \\( -name '.next' -o -name 'dist' -o -name '__pycache__' -o -name '.cache' \\) -type d -exec rm -rf {} + 2>/dev/null || true")
   Log: "Pre-debug cache cleanup complete."
```

#### Patch D3: Enhanced bug-investigator prompt
In the Agent Invocation section, when invoking `cc10x:bug-investigator`, append to the prompt:

```
## Bugfix Methodology (7-Phase — MANDATORY)

Follow the structured debug-workflow phases. Key additions to your standard process:

### Parallel Test Writer (Phase 3b)
After identifying root cause, spawn `debug-test-writer` agent in background:
Agent(debug-test-writer, run_in_background=true):
  Symptom: <what the user observed>
  Root cause: <why it happens>
  Affected code: <file paths and function names>
  Reproduction: <how to trigger the bug>

The test writer creates regression tests that FAIL on buggy code, working in parallel.

### BUGSTONE Pattern Sweep (Phase 5b — MANDATORY after fix)
After applying fix, sweep for sibling bugs:
1. Extract the bug pattern (what was wrong + correct usage)
2. `grep -rn` across ALL relevant file types (backend + frontend + tests)
3. Use multiple search terms (function name, error pattern, anti-pattern)
4. Fix ALL instances in the same commit — never fix just one
5. Report sweep count in Router Contract: PATTERN_SWEEP_COUNT: {N}

### Phase 7: Document (after verification)
Report documentation needs in Router Contract:
DOCUMENTATION:
  gotcha: "{title}" | null  # if counter-intuitive behavior
  debug_history: "{symptom} → {root_cause} → {fix}"
  instinct: "{trigger}" | null  # if pattern likely to recur
```

#### Patch D4: Document-debug task in task hierarchy
In the `### DEBUG Workflow Tasks` section, add after integration-verifier task:

```
TaskCreate({ subject: "CC10X document-debug: Update debug knowledge", description: "Phase 7 from debug-workflow. Execute INLINE (never spawn agent).\n\n1. If bug-investigator Router Contract has DOCUMENTATION.gotcha != null:\n   → Read docs/gotchas.md → Append gotcha entry (Symptom/Why/Fix/Example format)\n2. Always append to docs/debug-history.md:\n   → Date, symptom, root cause, fix, pattern sweep count\n3. If DOCUMENTATION.instinct != null:\n   → Create .claude/instincts/personal/{id}.md with trigger and confidence 0.5\n4. Ensure docs/ files exist (create with header if missing)", activeForm: "Documenting debug findings" })
# Returns document_task_id
TaskUpdate({ taskId: document_task_id, addBlockedBy: [verifier_task_id] })
```

Wire Memory Update to depend on document-debug instead of verifier:
```
TaskUpdate({ taskId: memory_task_id, addBlockedBy: [document_task_id] })  # was: [verifier_task_id]
```

#### Patch D5: DEBUG chain description update
Update the DEBUG chain in the Decision Tree from:
```
bug-investigator → code-reviewer → integration-verifier
```
to:
```
bug-investigator → code-reviewer → integration-verifier → document-debug
```

#### Patch D6: Router Contract extension for bug-investigator
In the Router Contract Validation section, add to bug-investigator's CONTRACT RULE:
```
| bug-investigator | ... (existing rules) AND PATTERN_SWEEP_COUNT must be >= 0 (field must exist) |
```

#### Patch D7: Document-debug execution in Chain Execution Loop
Add to the Chain Execution Loop, step 2:
```
- **Document-debug guard:** If task subject starts with "CC10X document-debug:":
  → Execute INLINE (Read + Edit calls in main context). NEVER spawn Task().
  → Read bug-investigator Router Contract from captured Memory Notes in memory_task_id description.
  → Extract DOCUMENTATION fields.
  → If gotcha: Read docs/gotchas.md → append entry → Read-back verify.
  → Always: Read docs/debug-history.md → append entry → Read-back verify.
  → If instinct: Write .claude/instincts/personal/{id}.md → Read-back verify.
  → TaskUpdate({ taskId, status: "completed" })
  → Continue to next runnable task. Do NOT proceed to agent routing logic.
```

### Step 4: Verify
```bash
grep -c "codex-review" "$ROUTER_FILE"   # Should be 5+ (BUILD patch)
grep -c "bugfix-knowledge-search" "$ROUTER_FILE"  # Should be 1+ (DEBUG patch)
grep -c "document-debug" "$ROUTER_FILE"  # Should be 3+ (DEBUG patch)
grep -c "PATTERN_SWEEP_COUNT" "$ROUTER_FILE"  # Should be 2+ (DEBUG patch)
```

## Rules

- **Idempotent** — check before each patch
- **Version-aware** — adapt if router structure changed
- **BUILD patches**: codex-review chain injection
- **DEBUG patches**: bugfix 7-phase methodology injection

## Prerequisites

BUILD patches require:
- `.claude/scripts/codex_review.py` — the review script
- `OPENAI_API_KEY_CODE_REVIEW` environment variable

DEBUG patches require:
- `.claude/skills/debug-workflow/SKILL.md` — the 7-phase debug workflow
- `.claude/agents/debug-test-writer.md` — the parallel test writer agent
- `docs/gotchas.md` and `docs/debug-history.md` — created automatically if missing
