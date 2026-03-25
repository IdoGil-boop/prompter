<!-- managed by claude-code-starter -->
---
name: create-cc10x-flow
description: Template and checklist for building new cc10x-compatible workflows with task DAGs, Router Contracts, CONTRACT RULEs, self-healing, and circuit breakers.
user_invocable: true
---

# Create cc10x-Compatible Flow

A reusable template for building workflows that enforce step completion through the same three-layer model used by cc10x BUILD and DEBUG flows. Use this skill whenever you need to create a new structured workflow that **cannot have steps skipped**.

---

## The Four-Layer Enforcement Model

Every cc10x-compatible flow enforces step completion through four independent layers. If any single layer fails, the others still prevent skipping.

### Layer 1: Structural (Task DAG)
Tasks are created upfront with `addBlockedBy` dependencies. A task **literally cannot run** until all its blockers reach `completed` status. This is the strongest enforcement — no prompt engineering can override it.

### Layer 2: Contractual (Router Contracts + CONTRACT RULEs)
Each phase outputs a structured YAML contract. The router validates contract fields against rules. If an agent claims SUCCESS but the contract evidence doesn't support it, the router **overrides the status to FAIL**.

### Layer 3: Behavioral (Self-Healing + Circuit Breaker)
When verification fails, the agent creates a REM-FIX task and **blocks itself** until the fix completes. A circuit breaker prevents infinite loops by escalating to the user after 3 active REM-FIX attempts.

### Layer 4: Documentation (Compaction-Safe Memory)
Every phase persists its key outputs to `.claude/cc10x/` memory files. If the conversation compacts mid-workflow, the chain of reasoning survives. This is **essential** for long workflows (30+ tool calls) like debugging, multi-phase builds, and migrations.

---

## Step 1: Define Your Phases

List every phase of your workflow. For each phase, answer:

| Question | Example (BUILD) | Example (DEBUG) |
|----------|-----------------|-----------------|
| What does this phase produce? | Working code + tests | Root cause statement |
| What evidence proves it was done? | TDD_RED_EXIT, TDD_GREEN_EXIT | ROOT_CAUSE, CONFIDENCE |
| Can it run in parallel with another phase? | Review + Hunt in parallel | Test writer + Hypothesize |
| Should it self-heal on failure? | Yes (REM-FIX) | Only verification |
| Should it execute inline (not delegated)? | Memory update | Documentation |

### Template: Phase Definition
```markdown
## Phase N: <Name>

**Task**: `<task_name>`
**Blocked by**: `[<upstream_task_1>, <upstream_task_2>]`
**Parallel with**: `<other_task>` or none
**Agent**: `<agent_name>` or inline
**Self-healing**: yes/no

<Phase instructions — what the agent must do>

### Router Contract (Phase N)
<YAML contract — see Step 3>

### CONTRACT RULE (Phase N)
<Validation rules — see Step 4>
```

---

## Step 2: Build the Task DAG

### 2a. Draw the Dependency Graph

Map phases to a directed acyclic graph (DAG). Rules:
- **Forward-only**: downstream blocked by upstream, never reverse
- **No cycles**: if A blocks B, B cannot block A (directly or transitively)
- **Parallel branches**: phases that don't depend on each other can run simultaneously
- **Join points**: phases that depend on multiple branches wait for ALL

```
# Template DAG — adapt to your workflow
phase_1 → phase_2 → phase_3 ──→ phase_5 → phase_6 → phase_7
                            └──→ phase_4 (parallel) ──┘
```

### 2b. Create Tasks at Workflow Start

Create ALL tasks upfront, then set dependencies. This ensures the full DAG exists before any phase executes.

```
# Create all tasks first
TaskCreate: task_1 ← "CC10X <FLOW>: <Phase 1 Name>"
TaskCreate: task_2 ← "CC10X <FLOW>: <Phase 2 Name>"
TaskCreate: task_3 ← "CC10X <FLOW>: <Phase 3 Name>"
...

# Then set all dependencies
TaskUpdate(task_2, addBlockedBy: [task_1])
TaskUpdate(task_3, addBlockedBy: [task_2])
...
```

### 2c. Task Naming Convention

All tasks MUST follow: `"CC10X <FLOW_TYPE>: <Phase Description>"`

Examples:
- `"CC10X BUILD: Component Builder"`
- `"CC10X DEBUG: Root Cause Analysis"`
- `"CC10X REVIEW: Security Scan"`
- `"CC10X DEPLOY: Pre-flight Checks"`

REM-FIX tasks: `"CC10X REM-FIX: <What Failed>"`

---

## Step 3: Define Router Contracts

Every phase outputs a Router Contract — a structured YAML block that declares what the phase accomplished. This is the **evidence** that the router validates.

### Template: Router Contract
```yaml
PHASE: <N>-<phase-name>
STATUS: <PASS|FAIL|specific-status>
<EVIDENCE_FIELD_1>: <value>
<EVIDENCE_FIELD_2>: <value>
...
```

### Contract Design Rules

1. **STATUS is always first** — the router checks this field to decide pass/fail
2. **Evidence fields are specific** — not "things_done: true" but "TDD_RED_EXIT: 1"
3. **Counts over booleans** — "TESTS_WRITTEN: 3" is harder to fake than "TESTS_WRITTEN: true"
4. **Exit codes over descriptions** — "LINTER_EXIT: 0" is verifiable, "linter passed" is not
5. **Lists over counts** — "FILES_CHANGED: ['a.ts', 'b.ts']" lets the router spot-check

### Good vs Bad Evidence Fields

| Good (hard to fake) | Bad (easy to fake) |
|---------------------|-------------------|
| `TDD_RED_EXIT: 1` | `TESTS_WRITTEN: true` |
| `FILES_CHANGED: ["a.ts"]` | `CODE_CHANGED: true` |
| `SCENARIOS_PASSED: 5` / `SCENARIOS_TOTAL: 5` | `ALL_PASSED: true` |
| `PATTERN_SEARCHED: "foo(null)"` | `SWEEP_DONE: true` |
| `CANDIDATES_CONSIDERED: 3` | `THOUGHT_ABOUT_IT: true` |

---

## Step 4: Define CONTRACT RULEs

CONTRACT RULEs are **automatic overrides** — they validate the Router Contract and override STATUS if evidence doesn't match the claim. The agent cannot bypass these.

### Template: CONTRACT RULE
```
STATUS=<claimed_status> but <evidence_field><operator><expected_value>
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="<human-readable explanation>"
```

### CONTRACT RULE Design Patterns

#### Pattern 1: Missing Evidence
```
STATUS=PASS but EVIDENCE_FIELD is empty or undefined
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="<field> is required but was not provided"
```

#### Pattern 2: Count Mismatch
```
STATUS=PASS but SCENARIOS_PASSED ≠ SCENARIOS_TOTAL
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Not all scenarios passed"
```

#### Pattern 3: Exit Code Validation
```
STATUS=PASS but EXIT_CODE ≠ 0
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Command exited with non-zero status"
```

#### Pattern 4: Minimum Threshold
```
STATUS=PASS but CONFIDENCE < MEDIUM
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Confidence too low to proceed"
```

#### Pattern 5: Cross-Field Consistency
```
STATUS=PASS but SIBLINGS_FOUND > SIBLINGS_FIXED
  → Override: STATUS=FAIL, BLOCKING=true,
    REMEDIATION_REASON="Found issues but didn't fix all of them"
```

---

## Step 5: Add Self-Healing (For Critical Phases)

Self-healing is for phases where failure should trigger automatic remediation, not just a FAIL status. Use it for **verification, review, and integration** phases — not for early investigative phases.

### Template: Self-Healing Protocol
```
If STATUS=FAIL:
  1. TaskCreate: rem_fix_task ← "CC10X REM-FIX: <What Failed>"
     description: "<what failed, what needs fixing, relevant contract fields>"
  2. TaskUpdate(current_task, addBlockedBy: [rem_fix_task])
     → current task blocks itself until fix completes
  3. Do NOT call TaskUpdate(current_task, status: "completed")
     → task stays in_progress, blocked by REM-FIX
  4. When rem_fix_task completes → re-run current phase verification
```

### When to Use Self-Healing

| Phase Type | Self-Healing? | Why |
|------------|--------------|-----|
| Investigation (reproduce, isolate) | No | Failures need human context |
| Analysis (root cause, hypothesize) | No | Can't auto-fix reasoning |
| Execution (build, fix, apply) | Sometimes | Only if fix criteria are clear |
| Verification (test, review, verify) | **Yes** | Clear pass/fail, fixable |
| Documentation (memory, docs) | No | Always succeeds or is trivial |

---

## Step 6: Add Circuit Breaker

Prevents infinite self-healing loops. Place this check **before** creating any REM-FIX task.

### Template: Circuit Breaker
```
BEFORE creating any REM-FIX task:
  Count ACTIVE REM-FIX tasks:
    TaskList() → filter (subject contains "CC10X REM-FIX:"
                  AND status IN [pending, in_progress])

  If count ≥ 3:
    → AskUserQuestion: "Too many active fix attempts ({N} active). How to proceed?"
      - "Research best practices (Recommended)"
      - "Fix locally"
      - "Accept known issues and document"
      - "Abort workflow"

  Do NOT count completed REM-FIX tasks — they are resolved.
```

---

## Step 7: Add Inline Execution Guards

Some phases MUST execute in the main context (inline), not be delegated to sub-agents. This is critical for:
- **Memory persistence** — sub-agents have stale memory
- **Final documentation** — must see full workflow context
- **Sensitive operations** — need main conversation context

### Template: Inline Guard
```
If task subject starts with "CC10X <FLOW> Memory:" or "CC10X <FLOW> Document:":
  → Execute INLINE (Read + Edit calls in main context)
  → NEVER spawn Agent() for this task
  → Follow task description instructions directly
  → Mark task completed inline
```

---

## Step 8: Add Memory Notes Preservation

For READ-ONLY agents (reviewers, analyzers), capture key findings in the task description so they survive context compaction.

### Template: Memory Notes
```
After any READ-ONLY agent completes:
  1. Locate "### Memory Notes" section in agent output
  2. TaskUpdate(memory_task, description: append Memory Notes)
  → If conversation compacts, memory notes are safe in task description
```

---

## Step 9: Add Documentation Layer (Compaction-Safe Memory)

Long workflows (30+ tool calls) **will** hit context compaction. Without persistent documentation, the chain of reasoning is lost mid-workflow. Every cc10x-compatible flow must persist its state to `.claude/cc10x/` memory files.

### Three Memory Files

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `activeContext.md` | Working memory — current focus, decisions, phase log | Every phase transition |
| `patterns.md` | Long-term memory — conventions, gotchas, reusable patterns | When patterns discovered |
| `progress.md` | Execution tracking — task status + verification evidence | After each phase completes |

### Template: Workflow Start (MANDATORY)

```
# Load memory (permission-free)
Bash(command="mkdir -p .claude/cc10x")
Read(file_path=".claude/cc10x/activeContext.md")
Read(file_path=".claude/cc10x/patterns.md")
Read(file_path=".claude/cc10x/progress.md")

# Initialize workflow context
Edit(old_string="## Current Focus",
     new_string="## Current Focus\n\n<FLOW_TYPE>: {description}")
Edit(old_string="## Recent Changes",
     new_string="## Recent Changes\n- [<FLOW>-0]: Workflow started — {context}")
```

### Template: Phase Logging

After each phase completes, log to `activeContext.md ## Recent Changes`:
```
Edit(old_string="## Recent Changes",
     new_string="## Recent Changes\n- [<FLOW>-N]: {phase_name} — {key_output}")
```

Use a consistent prefix per workflow type:
- `[BUILD-N]` for build workflows
- `[DEBUG-N]` for debug workflows
- `[DEPLOY-N]` for deploy workflows
- `[MIGRATE-N]` for migration workflows

### Template: Decision Logging

When making decisions during the workflow, persist immediately:
```
Edit(old_string="## Decisions",
     new_string="## Decisions\n- <Flow> [{date}]: {decision} — {reasoning}")
```

### Template: Progress Evidence

After verification steps, record hard evidence:
```
Edit(file_path=".claude/cc10x/progress.md",
     old_string="## Verification",
     new_string="## Verification\n- `{command}` → exit {code} ({passed}/{total})")
```

### Template: Pre-Compaction Safety

Update memory IMMEDIATELY when you notice:
- **High tool count** (30+ calls) — compaction imminent
- **Long iterative loops** (5+ cycles) — context filling fast
- **Switching contexts** frequently — hard to reconstruct
- **Key decision made** — reasoning will be lost

### Template: Workflow End (MANDATORY)

The final phase (documentation/memory update) MUST:
1. Write final phase log entry to activeContext.md
2. Update `## Current Focus` to reflect completion
3. Mark all tasks completed in progress.md with evidence
4. Persist any discovered patterns to patterns.md
5. Read-back verify each edit

### READ-ONLY Agent Memory Notes

Agents without Edit tool MUST output a `### Memory Notes` section:
```markdown
### Memory Notes (For Workflow-Final Persistence)
- **Learnings:** {insights for activeContext.md}
- **Patterns:** {conventions for patterns.md}
- **Evidence:** {verification results for progress.md}
```

The router captures these into the memory_task description (survives compaction).

---

## Checklist: Definition of Done

Before shipping a new cc10x-compatible flow, verify:

### Structural (Task DAG)
- [ ] All phases have corresponding tasks
- [ ] All dependencies are set via `addBlockedBy`
- [ ] DAG is acyclic (no circular dependencies)
- [ ] Parallel branches join correctly at downstream tasks
- [ ] All tasks created upfront before execution starts

### Contractual (Router Contracts)
- [ ] Every phase has a Router Contract YAML
- [ ] Evidence fields use hard-to-fake values (counts, exit codes, lists)
- [ ] Every phase has at least one CONTRACT RULE
- [ ] CONTRACT RULEs cover: missing evidence, count mismatches, exit codes

### Behavioral (Self-Healing)
- [ ] Verification/review phases have self-healing protocol
- [ ] REM-FIX tasks block the originating task
- [ ] Circuit breaker at 3 active REM-FIX tasks
- [ ] User escalation path exists for circuit breaker

### Documentation (Compaction-Safe Memory)
- [ ] Memory files loaded at workflow start (all 3)
- [ ] Phase log entries use `[FLOW-N]` format in activeContext.md
- [ ] Decisions persisted to `## Decisions` immediately when made
- [ ] Verification evidence recorded in progress.md
- [ ] Pre-compaction safety triggers defined (tool count, loop count)
- [ ] READ-ONLY agents output `### Memory Notes` section
- [ ] Final phase updates all 3 memory files + reads back to verify

### Execution
- [ ] Final documentation phase executes inline
- [ ] Memory Notes preservation for READ-ONLY agents
- [ ] Task naming follows `"CC10X <FLOW>: <Phase>"` convention
- [ ] Completion rule documented: workflow done when final task completes

---

## Example: Minimal 3-Phase Flow

```markdown
## Setup
Bash("mkdir -p .claude/cc10x")
Read(".claude/cc10x/activeContext.md")   # Load memory
Read(".claude/cc10x/patterns.md")
Read(".claude/cc10x/progress.md")
Edit(activeContext ## Recent Changes → "[EXAMPLE-0]: Workflow started")

## Task DAG
TaskCreate: analyze_task ← "CC10X EXAMPLE: Analyze"
TaskCreate: execute_task ← "CC10X EXAMPLE: Execute"
TaskCreate: verify_task  ← "CC10X EXAMPLE: Verify"

TaskUpdate(execute_task, addBlockedBy: [analyze_task])
TaskUpdate(verify_task, addBlockedBy: [execute_task])

## Phase 1: Analyze
Router Contract:
  PHASE: 1-analyze
  STATUS: COMPLETE
  FINDINGS: ["<f1>", "<f2>"]
CONTRACT RULE:
  STATUS=COMPLETE but FINDINGS is empty → FAIL
Memory: Edit(activeContext → "[EXAMPLE-1]: Analysis found {findings}")

## Phase 2: Execute
Router Contract:
  PHASE: 2-execute
  STATUS: APPLIED
  FILES_CHANGED: ["<path>"]
CONTRACT RULE:
  STATUS=APPLIED but FILES_CHANGED is empty → FAIL
Memory: Edit(activeContext → "[EXAMPLE-2]: Applied changes to {files}")

## Phase 3: Verify (self-healing)
Router Contract:
  PHASE: 3-verify
  STATUS: PASS|FAIL
  TEST_EXIT: <code>
CONTRACT RULE:
  STATUS=PASS but TEST_EXIT≠0 → FAIL
Self-Healing:
  If FAIL → REM-FIX + block self + re-verify
Circuit Breaker:
  3 active REM-FIX → AskUserQuestion
Memory: Edit(activeContext → "[EXAMPLE-3]: Verified — tests exit {code}")
        Edit(progress ## Verification → "`{cmd}` → exit {code}")

## Teardown (inline)
Edit(activeContext ## Current Focus → "EXAMPLE complete")
Edit(progress ## Completed → "[x] All phases — verified")
Read(activeContext)  # Verify
Read(progress)       # Verify
```
