<!-- managed by claude-code-starter -->
# Security Guidelines

## Mandatory Security Checks

Before ANY commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (use ORM or parameterized queries)
- [ ] XSS prevention (framework escaping, no raw HTML injection)
- [ ] CSRF protection on state-changing endpoints
- [ ] Authentication/authorization verified on all protected routes
- [ ] Rate limiting on public endpoints
- [ ] Error messages don't leak sensitive data (no stack traces in API responses)

## Secret Management

Never hardcode secrets. Use environment variables via a config module:
```
# BAD: api_key = "sk-proj-xxxxx"
# GOOD: api_key = settings.API_KEY  # validated at startup
```

## Input Validation

- Validate at system boundaries (user input, external APIs)
- Use schema validation (Pydantic, Zod, JSON Schema)
- Sanitize before database operations
- Whitelist over blacklist

## Authentication & Authorization

- Verify auth on every protected endpoint
- Use principle of least privilege
- Validate OAuth state parameters (prevent CSRF on callbacks)
- Never log tokens or credentials
- Store sensitive tokens encrypted at rest

## Security Scanning

Run before merging:
- Linters with security rules enabled
- Language-specific security scanners
- Dependency vulnerability scanners
- Type checkers (catch security-adjacent bugs)

## Security Response Protocol

If security issue found:
1. STOP immediately
2. Use **security-reviewer** agent
3. Fix CRITICAL issues before continuing
4. Rotate any exposed secrets
5. Review codebase for similar issues
