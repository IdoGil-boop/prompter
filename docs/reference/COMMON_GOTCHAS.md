<!-- managed by claude-code-starter -->
# Common Gotchas

Known pitfalls and workarounds. Add new entries as they're discovered.

## ORM / Database
<!-- Add database-specific gotchas as they're discovered -->

## Infrastructure

### Agent Workflow Diff Gates See Empty Diffs After Commit
**Symptom**: Conditional agents in multi-step workflows (e.g., mobile-auditor, security-reviewer) always skip because they detect no changed files.
**Cause**: The builder step commits changes before conditional agents run. `git diff --name-only HEAD` compares the working tree to the last commit — but since changes were just committed, the working tree is clean and the diff is empty.
**Fix**: Use `git diff --name-only HEAD~1 HEAD` instead. This compares the last commit against its parent, showing exactly what the builder step changed.

## Frontend
<!-- Add UI/React/build gotchas here -->

## Testing
<!-- Add test-specific gotchas here -->

## Language Pitfalls

### Falsy-Zero Bug: `x or default` Treats Valid `0` as Falsy
**Symptom**: Numeric fields with value `0` silently get replaced by the default, corrupting sort order and selections.
**Cause**: Python's `or` treats `0`, `0.0`, `""`, `None`, and `False` all as falsy. `score or 100` replaces a valid `0` with `100`.
**Fix**: Use explicit `None` check: `score if score is not None else 100`. For ANY numeric field where `0` is a valid value, NEVER use `or` for defaulting.

JavaScript equivalent: `x || default` has the same problem — use `x ?? default` (nullish coalescing) instead.

## API / Integration
<!-- Add external API gotchas here -->
