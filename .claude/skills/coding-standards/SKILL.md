<!-- managed by claude-code-starter -->
---
name: coding-standards
description: Universal coding standards. Type hints, logging, error handling, and quality principles.
---

# Coding Standards

## Universal Principles

1. **Type safety**: All public functions have type annotations
2. **Structured logging**: Use language-standard loggers, never print()
3. **Specific errors**: Catch specific exceptions with context, never bare except
4. **Small functions**: <50 lines, single responsibility
5. **Small files**: <800 lines, extract before exceeding
6. **No hardcoded values**: Use config or constants
7. **No deep nesting**: >4 levels = extract helper functions

## Before Committing

- [ ] Linter passes: `ruff check`
- [ ] Type checker passes: `mypy`
- [ ] Tests pass: `pytest`
- [ ] No print/console.log in production code
- [ ] No hardcoded secrets
