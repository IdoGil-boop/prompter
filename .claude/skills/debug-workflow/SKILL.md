<!-- managed by claude-code-starter -->
---
name: debug-workflow
description: Structured debugging skill with cc10x-compatible task DAG enforcement, Router Contracts, self-healing, and BUGSTONE pattern sweep.
user_invocable: true
---

# Debug Workflow (cc10x-Compatible)

Structured debugging methodology enforced through task dependencies, Router Contracts, and self-healing loops. Steps **cannot be skipped** — downstream tasks are blocked until upstream tasks complete.

> **ENFORCEMENT MODEL**: This workflow uses the same four-layer enforcement as the cc10x BUILD flow:
> 1. **Structural** — Task DAG with `addBlockedBy` prevents out-of-order execution
> 2. **Contractual** — Router Contract YAML validates each phase's outputs
> 3. **Self-healing** — Failures create REM-FIX tasks that block progress until resolved
> 4. **Documentation** — Every phase persists to `.claude/cc10x/` memory files (survives compaction)

---

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.
FIX THE ROOT CAUSE, NOT THE SYMPTOM.
```

**Never fix solely where errors appear — trace to the original trigger.** The place where a bug manifests (crash, wrong output, test failure) is almost never where the bug lives. Trace the call chain upward until you find the **original trigger** — the code that first introduced the invalid state.

A fix that patches the symptom location is a **cosmetic fix**. It will:
- Break in a different way when inputs change
- Leave sibling bugs untouched (BUGSTONE sweep finds nothing because the pattern was never fixed)
- Require another fix when the same root cause surfaces elsewhere

### Red Flags — STOP and Return to Root Cause

If you catch yourself thinking any of these, **STOP immediately** and return to Phase 3:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I see the problem, let me fix it" *(seeing symptoms ≠ understanding root cause)*
- "It's probably X, let me fix that" *(probably ≠ evidence)*
- "I don't fully understand but this might work"
- "One more fix attempt" *(after 2+ failed fixes)*
- Proposing solutions before tracing data flow

### Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need full process" | Simple issues have root causes too |
| "Emergency, no time for root cause" | Systematic debugging is FASTER than guess-and-check |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem, not a bug |
| "The fix works but I don't know why" | This isn't fixed, this is luck |

### 3-Fix Cap — Question Architecture

If 3+ fixes have been attempted and none resolved the issue:

1. **STOP** — do not attempt fix #4
2. **Question fundamentals**: Is the pattern/architecture sound?
3. **AskUserQuestion**: "3+ fixes failed. This suggests an architectural issue, not a simple bug. How to proceed?"
   - "Question architecture (Recommended)"
   - "Research externally"
   - "Continue with new hypothesis"
   - "Abort"

---

## Task DAG (Dependency Graph)

Create all tasks at workflow start. Downstream tasks are **physically blocked** until their dependencies complete.

```
TaskCreate: knowledge_search_task    ← "CC10X DEBUG: Knowledge Search"
TaskCreate: reproduce_task           ← "CC10X DEBUG: Reproduce Bug"
TaskCreate: isolate_task             ← "CC10X DEBUG: Isolate Bug"
TaskCreate: root_cause_task          ← "CC10X DEBUG: Root Cause Analysis"
TaskCreate: test_writer_task         ← "CC10X DEBUG: Parallel Test Writer"
TaskCreate: hypothesize_task         ← "CC10X DEBUG: Hypothesize Fix"
TaskCreate: fix_task                 ← "CC10X DEBUG: Apply Fix"
TaskCreate: pattern_sweep_task       ← "CC10X DEBUG: BUGSTONE Pattern Sweep"
TaskCreate: verify_task              ← "CC10X DEBUG: Verification"
TaskCreate: document_task            ← "CC10X DEBUG: Document Learnings"

# Dependencies (addBlockedBy):
reproduce_task       ← blocked by: [knowledge_search_task]
isolate_task         ← blocked by: [reproduce_task]
root_cause_task      ← blocked by: [isolate_task]
test_writer_task     ← blocked by: [root_cause_task]         # spawns in background
hypothesize_task     ← blocked by: [root_cause_task]         # runs parallel with test_writer
fix_task             ← blocked by: [hypothesize_task]
pattern_sweep_task   ← blocked by: [fix_task]
verify_task          ← blocked by: [pattern_sweep_task, test_writer_task]  # waits for BOTH
document_task        ← blocked by: [verify_task]
```

**Critical property**: All `addBlockedBy` calls are forward-only. The DAG has no cycles. A task CANNOT transition to `in_progress` until ALL its blockers have `completed` status.

---

## Documentation Layer (Compaction-Safe Memory)

Debugging sessions are **long** — often 30+ tool calls spanning reproduction, logging loops, hypothesis testing, and verification. Context compaction WILL happen. Without persistent documentation, the chain of reasoning (reproduction → root cause → fix rationale) is lost mid-debug.

### Three Memory Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `.claude/cc10x/activeContext.md` | Working memory — current focus, decisions, debug cycle log | Every phase transition |
| `.claude/cc10x/patterns.md` | Long-term memory — conventions, gotchas, architecture | When gotcha discovered |
| `.claude/cc10x/progress.md` | Execution tracking — task status, verification evidence | After each phase completes |

### At Workflow Start (MANDATORY)

```
Bash(command="mkdir -p .claude/cc10x")
Read(file_path=".claude/cc10x/activeContext.md")
Read(file_path=".claude/cc10x/patterns.md")
Read(file_path=".claude/cc10x/progress.md")
```

If any file doesn't exist, create it with the templates from `cc10x:session-memory`.

Initialize the debug session in activeContext.md:
```
Edit(old_string="## Current Focus",
     new_string="## Current Focus\n\nDEBUG: {bug_description}")

Edit(old_string="## Recent Changes",
     new_string="## Recent Changes\n- [DEBUG-0]: Workflow started — {symptom}")
```

### Debug Cycle Logging (Survive Compaction)

After each phase, append to `## Recent Changes` using the `[DEBUG-N]` format:

```
- [DEBUG-1]: Reproduced with `{command}` → {error}
- [DEBUG-2]: Isolated to {file}:{function}
- [DEBUG-3]: Root cause: {root_cause} (5 Whys: {chain})
- [DEBUG-4]: Chose fix approach: {approach} over {alternative} because {reason}
- [DEBUG-5]: Fix applied to {files} — {change_summary}
- [DEBUG-5b]: Pattern sweep: {pattern} → {hits} hits, {fixed} siblings fixed
- [DEBUG-6]: Verification: tests {pass/fail}, reproduction {fixed/still_broken}
- [DEBUG-7]: Documented: gotcha={yes/no}, history={yes}, instinct={yes/no}
```

**Why this matters**: If compaction happens between Phase 3 and Phase 5, the root cause and reproduction steps survive in activeContext.md. Without this, the fix phase has no context.

### Decision Logging

When making a decision during debugging, persist it immediately:
```
Edit(old_string="## Decisions",
     new_string="## Decisions\n- Debug [{date}]: {decision} — {reasoning}")
```

Examples:
- `Debug [2026-03-22]: Chose missing-index hypothesis over race-condition — timing is consistent, not intermittent`
- `Debug [2026-03-22]: Skipped gotcha for typo-class bug — not counter-intuitive`

### Pre-Compaction Safety Triggers

Update memory IMMEDIATELY when you notice:
- **5+ debug cycles** (logging loops) — high compaction risk
- **Switching between files** frequently — complex debugging
- **30+ tool calls** — approaching context limits
- **Hypothesis changed** — prior reasoning may be lost

Checkpoint pattern:
```
Edit(file_path=".claude/cc10x/activeContext.md",
     old_string="## Current Focus",
     new_string="## Current Focus\n\nDEBUG: {updated_focus}")
Read(file_path=".claude/cc10x/activeContext.md")  # Verify
```

### Progress Evidence (Hard Proof)

After each verification step, record evidence in progress.md:
```
Edit(old_string="## Verification",
     new_string="## Verification\n- `{test_command}` → exit {code} ({passed}/{total})")
```

### Memory Notes (For READ-ONLY Agents)

The `debug-test-writer` agent runs in background and cannot edit memory files. It MUST output a `### Memory Notes` section:
```markdown
### Memory Notes (For Workflow-Final Persistence)
- **Learnings:** Tests written for {pattern}, discovered {edge_case}
- **Test file:** {path}
- **RED confirmation:** `{command}` → exit {code}
```

The router captures these Memory Notes into the memory_task description (compaction-safe).

### At Workflow End (MANDATORY)

The `document_task` (Phase 7) executes inline and MUST:
1. Update `activeContext.md` — final `[DEBUG-7]` entry + update `## Current Focus`
2. Update `progress.md` — mark all tasks completed with verification evidence
3. Update `patterns.md` — add gotcha to `## Common Gotchas` if applicable
4. Update `docs/gotchas.md` and `docs/debug-history.md` (project-level docs)

---

## Phase 0: Knowledge Search

**Task**: `knowledge_search_task`
**Blocked by**: nothing (entry point)

Search existing project knowledge before touching any code.

1. Read `docs/gotchas.md` — check if this bug matches a known gotcha
2. Read `docs/debug-history.md` — check if a similar bug was fixed before
3. Search instincts: `grep -r "domain: debugging" .claude/instincts/`

Prior matches **accelerate** but never skip phases. Prior fixes can be wrong, outdated, or partial.

### Router Contract (Phase 0)
```yaml
PHASE: 0-knowledge-search
STATUS: COMPLETE
GOTCHAS_CHECKED: true|false
HISTORY_CHECKED: true|false
INSTINCTS_CHECKED: true|false
PRIOR_MATCH_FOUND: true|false
PRIOR_MATCH_SUMMARY: "<summary or N/A>"
```

### CONTRACT RULE
```
STATUS=COMPLETE but (GOTCHAS_CHECKED≠true OR HISTORY_CHECKED≠true)
  → Override: STATUS=INCOMPLETE, BLOCKING=true,
    REMEDIATION_REASON="Must read docs/gotchas.md AND docs/debug-history.md before proceeding"
```

**Memory update**: Log `[DEBUG-0]: Knowledge search — {matches_found_or_none}` to activeContext.md `## Recent Changes`

→ `TaskUpdate(knowledge_search_task, status: "completed")`

---

## Phase 1: Reproduce

**Task**: `reproduce_task`
**Blocked by**: `[knowledge_search_task]`

Consistently trigger the bug before attempting any fix.

- Capture: error message, stack trace, environment, triggering input
- Document exact reproduction steps (commands, URLs, user actions)
- If intermittent: establish frequency and conditions
- **Actually run the reproduction** and observe the failure yourself
- Pre-hook cleans caches (`.next/`, `dist/`, `__pycache__/`, `.cache/`)

### Router Contract (Phase 1)
```yaml
PHASE: 1-reproduce
STATUS: REPRODUCED|NOT_REPRODUCIBLE|INTERMITTENT
REPRODUCTION_COMMAND: "<exact command or steps>"
OBSERVED_ERROR: "<error message or behavior>"
ENVIRONMENT: "<relevant env details>"
```

### CONTRACT RULE
```
STATUS=REPRODUCED but REPRODUCTION_COMMAND is empty
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Must provide exact reproduction steps"

STATUS=NOT_REPRODUCIBLE
  → BLOCKING=true, trigger AskUserQuestion:
    "Bug cannot be reproduced. Provide more context / Try different environment / Abort?"
```

**Memory update**: Log `[DEBUG-1]: Reproduced with '{command}' → {error}` to activeContext.md `## Recent Changes`

→ `TaskUpdate(reproduce_task, status: "completed")`

---

## Phase 2: Isolate

**Task**: `isolate_task`
**Blocked by**: `[reproduce_task]`

Narrow the problem space.

- Binary search debugging: comment out halves of suspect code
- Targeted logging at suspect boundaries
- Check recent changes: `git log --oneline -20` and `git diff HEAD~5`
- Distinguish primary failure from cascading symptoms

### Router Contract (Phase 2)
```yaml
PHASE: 2-isolate
STATUS: ISOLATED|NEEDS_MORE_LOGGING
FILES_IDENTIFIED: ["<path1>", "<path2>"]
FUNCTIONS_IDENTIFIED: ["<func1>", "<func2>"]
NARROWED_TO: "<specific lines or logic block>"
```

### CONTRACT RULE
```
STATUS=ISOLATED but FILES_IDENTIFIED is empty
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Must identify specific files before proceeding"
```

→ `TaskUpdate(isolate_task, status: "completed")`

---

## Phase 3: Root Cause Analysis

**Task**: `root_cause_task`
**Blocked by**: `[isolate_task]`

Work backward from where the problem manifests. **Trace to the original trigger, not the symptom location.**

- Reconstruct context: request parameters, system state, execution timing
- Apply **5 Whys**: ask "why" iteratively to drill past symptoms
- **Root Cause Tracing**: follow the call chain upward from where the error manifests until you find where invalid state was first introduced
  ```
  1. Where does error manifest? (symptom location)
  2. What called this with bad data?
  3. Keep tracing up — follow invalid data backward
  4. Find original trigger — where did problem actually START?
  5. THAT is the root cause. Fix THERE, not at the symptom.
  ```
- Add targeted logging if needed (iterative logging loop)
- Do NOT proceed until root cause is clear

### Hypothesis Confidence Scoring

Track 2-3 hypotheses with confidence levels. **Never proceed to fix until one reaches 80+.**

```
H1: [hypothesis] — Confidence: [0-100]
    Evidence for: [what supports this]
    Evidence against: [what contradicts this]
    Next test: [what would raise or lower confidence]

H2: [hypothesis] — Confidence: [0-100]
    ...
```

| Range | Meaning | Action |
|-------|---------|--------|
| 80-100 | Strong evidence | Proceed to fix |
| 50-79 | Needs more data | Run "Next test" |
| 0-49 | Speculation | Deprioritize or discard |

### Router Contract (Phase 3)
```yaml
PHASE: 3-root-cause
STATUS: IDENTIFIED|NEEDS_MORE_INVESTIGATION
ROOT_CAUSE: "<clear statement of WHY, not just WHERE>"
ROOT_CAUSE_LOCATION: "<file:line where the bug ORIGINATES, not where it manifests>"
SYMPTOM_LOCATION: "<file:line where the error is OBSERVED>"
FIVE_WHYS_CHAIN: "<the chain you followed>"
CONFIDENCE: <0-100>
HYPOTHESES_TRACKED: <count — must be ≥2>
FIX_TARGET: "ROOT_CAUSE|SYMPTOM"
```

### CONTRACT RULE
```
STATUS=IDENTIFIED but CONFIDENCE<80
  → Override: STATUS=NEEDS_MORE_INVESTIGATION, BLOCKING=true,
    REMEDIATION_REASON="Confidence below 80 — gather more evidence before fixing"

STATUS=IDENTIFIED but ROOT_CAUSE is empty
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Must state root cause clearly"

STATUS=IDENTIFIED but FIX_TARGET=SYMPTOM
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Fix targets symptom location, not root cause. Trace the call chain upward to the original trigger."

STATUS=IDENTIFIED but ROOT_CAUSE_LOCATION=SYMPTOM_LOCATION
  → WARNING (not blocking): Verify this is genuinely the same location.
    If the root cause truly originates where the symptom appears, document why.

STATUS=IDENTIFIED but HYPOTHESES_TRACKED<2
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Must track at least 2 hypotheses to avoid confirmation bias"
```

**Memory update**: Log `[DEBUG-3]: Root cause: {root_cause} (5 Whys: {chain})` to activeContext.md `## Recent Changes`. Also persist as a Decision: `Debug [{date}]: Root cause identified — {root_cause}`

→ `TaskUpdate(root_cause_task, status: "completed")`

---

## Phase 3b: Spawn Parallel Test Writer

**Task**: `test_writer_task`
**Blocked by**: `[root_cause_task]`

Spawn `debug-test-writer` agent **in background** immediately after root cause is identified:

```
Agent(debug-test-writer, run_in_background=true):
  Symptom: <from Phase 1 contract: OBSERVED_ERROR>
  Root cause: <from Phase 3 contract: ROOT_CAUSE>
  Affected code: <from Phase 2 contract: FILES_IDENTIFIED, FUNCTIONS_IDENTIFIED>
  Reproduction: <from Phase 1 contract: REPRODUCTION_COMMAND>
```

The test writer runs in parallel with Phases 4-5. It writes regression tests that **fail now** (RED) and will **pass after the fix** (GREEN). It does NOT modify source code — only test files.

### Router Contract (Phase 3b)
```yaml
PHASE: 3b-test-writer
STATUS: TESTS_READY|TESTS_FAILED_TO_WRITE
AGENT_ID: "<agent ID>"
TEST_FILE: "<path to test file>"
TESTS_WRITTEN: <count>
TDD_RED_EXIT: <exit code — MUST be non-zero>
TEST_NAMES: ["<test1>", "<test2>"]
```

### CONTRACT RULE
```
STATUS=TESTS_READY but TDD_RED_EXIT=0
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Tests pass BEFORE fix — they don't capture the bug. Rewrite tests."

STATUS=TESTS_READY but TESTS_WRITTEN=0
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="No tests written"
```

→ `TaskUpdate(test_writer_task, status: "completed")`

---

## Phase 4: Hypothesize

**Task**: `hypothesize_task`
**Blocked by**: `[root_cause_task]`  (runs parallel with test_writer_task)

Generate candidate fixes before writing code.

- Propose 1-3 targeted fixes based on root cause
- Evaluate each: correctness, side effects, regression risk
- Prefer the **minimal change** that addresses root cause, not symptoms

### Router Contract (Phase 4)
```yaml
PHASE: 4-hypothesize
STATUS: APPROACH_CHOSEN
CANDIDATES_CONSIDERED: <count>
CHOSEN_APPROACH: "<description>"
RATIONALE: "<why this approach>"
RISK_ASSESSMENT: "<what could go wrong>"
```

### CONTRACT RULE
```
STATUS=APPROACH_CHOSEN but CANDIDATES_CONSIDERED<2
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Must consider at least 2 candidates before choosing"
```

→ `TaskUpdate(hypothesize_task, status: "completed")`

---

## Phase 5: Fix

**Task**: `fix_task`
**Blocked by**: `[hypothesize_task]`

Apply the chosen fix **at the root cause location, not the symptom location**.

- Make the minimal change that addresses root cause
- Follow existing code patterns and style
- The parallel `debug-test-writer` agent is writing regression tests concurrently
- **The fix must change code at or upstream of ROOT_CAUSE_LOCATION from Phase 3**
- If the fix only touches SYMPTOM_LOCATION, it's a cosmetic fix — go back

### Anti-Hardcode Gate (REQUIRED before implementing)

Before writing the fix, check whether the bug depends on **variants**:

| Variant Dimension | Example |
|-------------------|---------|
| Locale/i18n | Language, RTL/LTR, number formatting |
| Configuration/environment | Feature flags, env vars, build modes |
| Roles/permissions | Admin vs user, auth vs unauth |
| Data shape | Missing fields, empty lists, null values, ordering |
| Platform/runtime | Browser, OS, Node version |
| Concurrency/ordering | Races, retries, eventual consistency |

If variants apply, the fix MUST be **general** — it must work across all relevant variant dimensions, not just the one reproduction case. The regression test (from the parallel test writer) MUST cover at least one **non-default** variant.

### Router Contract (Phase 5)
```yaml
PHASE: 5-fix
STATUS: APPLIED
FILES_CHANGED: ["<path1>", "<path2>"]
CHANGE_SUMMARY: "<what was changed and why>"
LINES_CHANGED: <count>
FIX_LOCATION: "<file:line where the fix was applied>"
ROOT_CAUSE_LOCATION: "<file:line from Phase 3 — must match or be upstream>"
VARIANTS_CHECKED: true|false
VARIANTS_APPLICABLE: ["<dimension1>", "<dimension2>"] or []
HARDCODED: true|false
```

### CONTRACT RULE
```
STATUS=APPLIED but FILES_CHANGED is empty
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="No files were changed — fix not applied"

STATUS=APPLIED but FIX_LOCATION does not match or precede ROOT_CAUSE_LOCATION
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Fix applied at symptom location, not root cause. Trace upward and fix where the bug originates."

STATUS=APPLIED but VARIANTS_CHECKED≠true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Anti-Hardcode Gate not completed. Check variant dimensions before fixing."

STATUS=APPLIED but HARDCODED=true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Fix is hardcoded to one case. Must be general across applicable variants."
```

**Memory update**: Log `[DEBUG-5]: Fix applied to {files} — {change_summary}` to activeContext.md `## Recent Changes`

→ `TaskUpdate(fix_task, status: "completed")`

---

## Phase 5b: Pattern Sweep (BUGSTONE)

**Task**: `pattern_sweep_task`
**Blocked by**: `[fix_task]`

**MANDATORY** — never fix just one instance.

1. **Extract the pattern**: What was wrong and what correct usage looks like
2. **Search broadly**: `grep -rn` across ALL relevant file types (backend + frontend + tests)
3. **Use multiple search terms** (function name, error pattern, anti-pattern)
4. **Review each hit**: Confirm genuine instance of same bug class
5. **Fix ALL instances** in the same pass

### Router Contract (Phase 5b)
```yaml
PHASE: 5b-pattern-sweep
STATUS: SWEEP_COMPLETE
PATTERN_SEARCHED: "<the anti-pattern>"
SEARCH_TERMS_USED: ["<term1>", "<term2>"]
TOTAL_HITS: <count>
SIBLINGS_FOUND: <count>
SIBLINGS_FIXED: <count>
FILES_AFFECTED: ["<path1>", ...] or []
```

### CONTRACT RULE
```
PATTERN_SEARCHED is empty or undefined
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="CONTRACT RULE violated: BUGSTONE pattern sweep not performed — run grep -rn for sibling bugs"

SIBLINGS_FOUND > SIBLINGS_FIXED
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Found siblings but didn't fix all of them"
```

→ `TaskUpdate(pattern_sweep_task, status: "completed")`

---

## Phase 6: Verify (Fix Meets Tests)

**Task**: `verify_task`
**Blocked by**: `[pattern_sweep_task, test_writer_task]` — waits for BOTH

### 6a. Collect Parallel Test Results
- Wait for `debug-test-writer` agent to complete
- Review regression tests — ensure they target the actual bug
- Tests should have been verified as **failing (RED)** before the fix

### 6b. Run Tests — Must Turn GREEN
- Run new regression tests: `pytest <test_file> -v`
- They MUST pass now. If not:
  - Fix is incomplete → create REM-FIX task (self-healing)
  - Test is wrong → adjust test
- This is the **RED→GREEN contract**

### 6c. Full Verification
- Run original reproduction — must no longer trigger the bug
- Run full test suite: `pytest`
- Run linter and type checker: `ruff check` and `mypy`

### Router Contract (Phase 6)
```yaml
PHASE: 6-verify
STATUS: PASS|FAIL
REGRESSION_TESTS_COUNT: <count>
TDD_GREEN_EXIT: <exit code — MUST be 0>
RED_GREEN_CONFIRMED: true|false
FULL_SUITE_EXIT: <exit code>
REPRODUCTION_FIXED: true|false
LINTER_EXIT: <exit code>
```

### CONTRACT RULE
```
STATUS=PASS but TDD_GREEN_EXIT≠0
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Regression tests still failing after fix"

STATUS=PASS but RED_GREEN_CONFIRMED≠true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="RED→GREEN contract not confirmed"

STATUS=PASS but REPRODUCTION_FIXED≠true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Original reproduction still triggers the bug"
```

### Self-Healing Protocol (Phase 6)
```
If STATUS=FAIL:
  1. TaskCreate: rem_fix_task ← "CC10X REM-FIX: Verification Failed"
     description: "<what failed and what needs fixing>"
  2. TaskUpdate(verify_task, addBlockedBy: [rem_fix_task])
     → verify_task blocks itself until fix completes
  3. Do NOT call TaskUpdate(verify_task, status: "completed")
  4. When rem_fix_task completes → re-run Phase 6 verification
```

### Circuit Breaker
```
Before creating any REM-FIX task:
  Count ACTIVE REM-FIX tasks (pending or in_progress)
  If count ≥ 3:
    → AskUserQuestion: "Too many active fix attempts ({N} active). How to proceed?"
      - "Research best practices (Recommended)"
      - "Fix locally"
      - "Accept known issues and document"
      - "Abort workflow"
```

**Memory update**: Log `[DEBUG-6]: Verification {pass/fail} — tests: {count} GREEN, reproduction: {fixed/broken}` to activeContext.md `## Recent Changes`. Record verification evidence in progress.md `## Verification`.

→ `TaskUpdate(verify_task, status: "completed")`

---

## Phase 7: Document

**Task**: `document_task`
**Blocked by**: `[verify_task]`

**Execute INLINE** — never delegate to a sub-agent (memory persistence requires main context).

### 7a. Update Gotchas (if applicable)

If the bug was counter-intuitive (not just a typo), add to `docs/gotchas.md`:
```markdown
### [Short descriptive title]
**Symptom:** What the developer observes
**Why it happens:** The underlying cause
**Fix/Workaround:** The correct approach
**Example:**
  - Bad: `code that triggers the gotcha`
  - Good: `code that avoids the gotcha`
**Related:** [commit hash or PR link]
```

### 7b. Update Debug History (MANDATORY — always)

Append to `docs/debug-history.md`:
```markdown
### [Date] — [Short title]
**Symptom:** [What was observed]
**Root cause:** [The actual underlying issue]
**Fix:** [What was changed, with commit ref]
**Pattern sweep:** [How many siblings found and fixed, or "none"]
**Time to fix:** [Rough estimate]
```

### 7c. Consider Instinct

If likely to recur, create instinct in `.claude/instincts/personal/`:
```yaml
---
id: <descriptive-id>
trigger: "<when this applies>"
confidence: 0.5
domain: "debugging"
source: "bug-fix"
created: "{{today}}"
---
```

### Router Contract (Phase 7)
```yaml
PHASE: 7-document
STATUS: DOCUMENTED
GOTCHA_ADDED: true|false
GOTCHA_REASON: "<why or why not>"
HISTORY_UPDATED: true|false
INSTINCT_CREATED: true|false
INSTINCT_REASON: "<why or why not>"
```

### CONTRACT RULE
```
STATUS=DOCUMENTED but HISTORY_UPDATED≠true
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Debug history MUST be updated for every fix"
```

→ `TaskUpdate(document_task, status: "completed")`

---

## Quick Reference

| Phase | Task | Blocked By | Contract Key | Self-Healing |
|-------|------|------------|-------------|-------------|
| 0 | Knowledge Search | — | GOTCHAS_CHECKED, HISTORY_CHECKED | No |
| 1 | Reproduce | Phase 0 | STATUS=REPRODUCED, REPRODUCTION_COMMAND | AskUser if not reproducible |
| 2 | Isolate | Phase 1 | FILES_IDENTIFIED, FUNCTIONS_IDENTIFIED | No |
| 3 | Root Cause | Phase 2 | ROOT_CAUSE, CONFIDENCE≥80, FIX_TARGET=ROOT_CAUSE, HYPOTHESES≥2 | No |
| 3b | Test Writer | Phase 3 | TDD_RED_EXIT≠0 (background) | No |
| 4 | Hypothesize | Phase 3 | CANDIDATES_CONSIDERED≥2 | No |
| 5 | Fix | Phase 4 | FILES_CHANGED, FIX_LOCATION=ROOT_CAUSE, HARDCODED=false | No |
| 5b | Pattern Sweep | Phase 5 | PATTERN_SEARCHED, SIBLINGS | No |
| 6 | Verify | Phase 5b + 3b | TDD_GREEN_EXIT=0, RED_GREEN=true | Yes (REM-FIX + circuit breaker) |
| 7 | Document | Phase 6 | HISTORY_UPDATED=true | No |

> **Completion rule**: The workflow is NOT done until `document_task` status is `completed`. The DAG enforces this — document_task cannot complete until verify_task completes, which cannot complete until pattern_sweep_task AND test_writer_task complete, and so on back to knowledge_search_task.
