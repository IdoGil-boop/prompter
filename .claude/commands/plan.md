<!-- managed by claude-code-starter -->
---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

Invokes the **planner** agent to create a comprehensive implementation plan.

## What This Command Does

1. **Restate Requirements** — Clarify what needs to be built
2. **Identify Risks** — Surface potential issues and blockers
3. **Create Step Plan** — Break down into phases
4. **Wait for Confirmation** — MUST receive user approval before proceeding

**CRITICAL**: The planner agent will NOT write any code until you explicitly confirm.

## After Planning

- Use `/tdd` to implement with test-driven development
- Use `/code-review` to review completed implementation
- Use `/test-coverage` to verify coverage
