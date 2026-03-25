<!-- managed by claude-code-starter -->
---
description: Enforce test-driven development workflow. Write tests FIRST, then implement.
---

# TDD Command

Enforces the RED → GREEN → REFACTOR cycle.

## Workflow

1. **Scaffold interfaces** — Define the API/function signatures
2. **Write tests FIRST** — Cover happy path + edge cases
3. **Run tests** — Must FAIL (RED): `pytest backend/tests/test_feature.py -x`
4. **Implement** — Minimal code to pass
5. **Run tests** — Must PASS (GREEN)
6. **Refactor** — Clean up while keeping tests green
7. **Verify coverage**: `pytest --cov=app --cov-report=term-missing`

## Rules

- **Never skip RED phase** — if tests pass without implementation, they're wrong
- **80% minimum** coverage for new code
- **100% for security-critical code** (auth, tokens, input validation)
