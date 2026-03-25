<!-- managed by claude-code-starter -->
---
description: Review recent code changes for quality, security, and best practices
---

# Code Review

Comprehensive quality and security review of uncommitted changes.

## Steps

1. **Get changed files**: `git diff --name-only HEAD`
2. **Run static analysis**:
   ```bash
   ruff check backend/app/
   mypy backend/app/
   ```
3. **Review each changed file** for the categories below
4. **Generate report** with severity, file, line, description, fix
5. **Block commit** if CRITICAL or HIGH issues remain

## Review Categories

### CRITICAL (Must Fix)
- Hardcoded credentials, API keys, tokens
- SQL injection (raw SQL without parameterization)
- Unsafe eval/exec/pickle usage
- Missing input validation on API endpoints

### HIGH (Should Fix)
- N+1 query patterns
- Functions > 50 lines, files > 800 lines, nesting > 4 levels
- Missing error handling or bare except
- Missing type hints on public functions

### MEDIUM (Consider)
- Missing docstrings on public functions
- TODO/FIXME without linked issues
- Missing tests for new code paths
- Competing logic (violates single source of truth)

## Approval Criteria

| Status | Condition |
|--------|-----------|
| Approve | No CRITICAL or HIGH issues |
| Warning | Only MEDIUM issues |
| Block | CRITICAL or HIGH issues found |
