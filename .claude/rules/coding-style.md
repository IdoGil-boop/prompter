<!-- managed by claude-code-starter -->
# Coding Style

## Naming Conventions

Follow language-standard naming:
- **Python**: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- **JavaScript/TypeScript**: `camelCase` functions/variables, `PascalCase` classes/components, `UPPER_SNAKE_CASE` constants
- **Go**: `camelCase` unexported, `PascalCase` exported

## File Organization

MANY SMALL MODULES > FEW LARGE MODULES:
- Target 200-400 lines per module
- Hard maximum: 800 lines (extract before exceeding)
- Organize by feature/domain, not by type
- One class per file for complex models; group related small classes

## Immutability Patterns

Prefer creating new objects over in-place mutation:
- Use frozen dataclasses, NamedTuples, or readonly types
- Exception: ORM models that require mutation (use proper change tracking)

## Error Handling

- Raise specific exceptions with context (never bare `except`)
- Catch specific exceptions, not generic `Exception`
- Never swallow errors silently — log and re-raise or handle explicitly
- Include diagnostic context in error messages (IDs, counts, states)

## Logging

- Use structured logging with the language's standard logger
- Never use `print()` / `console.log()` in production code
- Include context fields: IDs, counts, timing, operation names
- Log levels: DEBUG for tracing, INFO for milestones, WARNING for recoverable issues, ERROR for failures

## Type Safety

All public functions MUST have type annotations:
- Python: type hints on all parameters and return types
- TypeScript: explicit types on exports, avoid `any`
- Use strict mode where available

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines, single responsibility)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels — extract helper functions)
- [ ] Proper error handling (no bare except, no silent swallowing)
- [ ] No print/console.log in production code (use logging)
- [ ] No hardcoded values (use config or constants)
- [ ] Type annotations on all public functions
- [ ] Linters pass
