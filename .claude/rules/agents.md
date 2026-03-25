<!-- managed by claude-code-starter -->
# Agent Orchestration

## Available Agents

Located in `.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| **planner** | Implementation planning | Complex features, multi-phase refactoring |
| **architect** | System design | Schema changes, system redesign, new subsystems |
| **tdd-guide** | Test-driven development | New features, bug fixes, security-critical code |
| **code-reviewer** | Code quality review | After writing code; catches common gotchas |
| **security-reviewer** | Security analysis | Auth changes, input handling, secrets management |
| **refactor-cleaner** | Dead code cleanup | Post-migration cleanup, removing competing logic |
| **post-session-maintainer** | Session capture | End-of-session: captures learnings |
| **mobile-auditor** | Mobile UX audit | Before release, after frontend changes, UI redesign |
| **ux-ui-advisor** | UX/UI review (CandleKeep-backed) | Frontend/UI changes; consults design reference books |
| **security-privacy-advisor** | Security & privacy review (CandleKeep-backed) | Auth, crypto, data handling changes; consults security books |
| **debug-test-writer** | Parallel regression tests during debugging | Auto-spawned by `/bugfix` at Phase 3b |
| **orchestrator** | Agent routing | Lists agents and recommends which to use |

## Immediate Agent Usage (No User Prompt Needed)

Trigger agents automatically in these situations:
1. **Complex feature request** — Use **planner** to break into phases
2. **Code just written/modified** — Use **code-reviewer**
3. **Bug fix or new feature** — Use **tdd-guide** to enforce write-tests-first
4. **Architectural decision** — Use **architect** for schema/system changes
5. **Security-sensitive changes** — Use **security-reviewer** or **security-privacy-advisor** (CandleKeep-backed)
6. **Frontend/UI changes** — Use **ux-ui-advisor** for design principle review (CandleKeep-backed)

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: code-reviewer on new logic
2. Agent 2: security-reviewer on auth changes
3. Agent 3: tdd-guide writing test stubs

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split-role sub-agents:
- **Factual reviewer** — Are the computations correct?
- **Senior engineer** — Is the architecture sound?
- **Security expert** — Any injection, data leakage, or auth issues?
- **Consistency reviewer** — Does this align with single-source-of-truth principle?
- **Redundancy checker** — Are we creating competing logic?
