<!-- managed by claude-code-starter -->
---
description: Create a new cc10x-compatible workflow with task DAG enforcement, Router Contracts, and self-healing
---

# Create cc10x Flow

Create a new structured workflow that enforces step completion through the cc10x three-layer model.

## Usage

Describe the workflow you want to create, and this command will guide you through building it with:

1. **Task DAG** — define phases and dependencies (prevents out-of-order execution)
2. **Router Contracts** — define evidence each phase must produce
3. **CONTRACT RULEs** — define automatic validation that overrides false claims
4. **Self-Healing** — define which phases auto-remediate on failure
5. **Circuit Breaker** — prevent infinite remediation loops

## Steps

1. **Gather requirements**: Ask the user what the workflow should accomplish
2. **Load the template**: Read the `create-cc10x-flow` skill for the full template and checklist
3. **Define phases**: List all phases with their dependencies and evidence requirements
4. **Draw the DAG**: Map phase dependencies, identify parallel branches and join points
5. **Write Router Contracts**: Define YAML contracts with hard-to-fake evidence fields
6. **Write CONTRACT RULEs**: Add validation rules for each contract
7. **Add self-healing**: For verification/review phases, add REM-FIX + block pattern
8. **Add circuit breaker**: 3 active REM-FIX cap with user escalation
9. **Verify against checklist**: Run the Definition of Done checklist from the skill
10. **Output**: Generate the SKILL.md, command .md, and any agent .md files needed

## Output Structure

The command produces:
- `base/.claude/skills/<flow-name>/SKILL.md` — the workflow definition
- `base/.claude/commands/<flow-name>.md` — the command entry point
- `base/.claude/agents/<agent>.md` — any new agents the flow needs
- Updated `base/.claude/skills/INDEX.md`
- Updated `base/.claude/rules/agents.md` (if new agents)
