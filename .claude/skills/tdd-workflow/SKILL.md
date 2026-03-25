<!-- managed by claude-code-starter -->
---
name: tdd-workflow
description: Test-driven development workflow skill. Enforces write-tests-first with 80%+ coverage.
---

# TDD Workflow

## RED → GREEN → REFACTOR

1. **RED**: Write a failing test that describes expected behavior
2. **Run**: `pytest backend/tests/test_feature.py -x` — must FAIL
3. **GREEN**: Write minimal code to pass
4. **Run**: must PASS
5. **REFACTOR**: Clean up, remove duplication
6. **Coverage**: `pytest --cov=app --cov-report=term-missing` — verify 80%+

## Test Priorities

1. Unit tests for all public functions
2. Integration tests for API endpoints and DB operations
3. E2E tests for critical user flows

## Edge Cases to Always Test

- None/empty inputs
- Boundary values (0, max, negative)
- Error paths (not just happy path)
- Concurrent access (if applicable)
