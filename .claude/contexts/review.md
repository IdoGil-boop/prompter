<!-- managed by claude-code-starter -->
# Review Mode

Code review context. Focus on quality, security, and patterns.

## Checklist

### Security
- [ ] No hardcoded secrets
- [ ] Input validation on all endpoints
- [ ] Parameterized queries (no SQL injection)
- [ ] Auth on protected routes

### Quality
- [ ] Functions <50 lines
- [ ] Files <800 lines
- [ ] Type annotations on public functions
- [ ] No bare except / silent error swallowing
- [ ] No print() in production code

### Testing
- [ ] 80%+ coverage for new code
- [ ] Edge cases covered
- [ ] Tests are independent

### Architecture
- [ ] Single source of truth respected
- [ ] No duplicate logic
- [ ] Follows existing patterns
