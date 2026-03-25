<!-- managed by claude-code-starter -->
# Stash Recovery

Safely recover a git stash created before a merge or branch change.

## The Problem

When a stash predates a merge commit, `git diff HEAD stash@{N}` shows merge-added files as "deletions." These are NOT intentional deletions.

## Recovery Checklist

### 1. Inventory
```bash
git stash list
git stash show -p stash@{0} --stat
git log --oneline --all --graph -10
```

### 2. Identify merge-added files
```bash
git diff-tree --no-commit-id -r --name-status <merge-commit>
```
Files with status `A` were introduced by the merge — MUST NOT be deleted.

### 3. Classify stash diff entries

| Scenario | Action |
|----------|--------|
| File existed before merge and stash removes it | Genuine deletion — apply |
| File was Added by merge | NOT a deletion — keep |
| Modified by both stash and merge | Resolve manually |

### 4. Apply safely
```bash
# Safer: apply without dropping
git stash apply stash@{0}
# Verify, THEN drop
git stash drop stash@{0}
```

### 5. Verify
```bash
# Run tests immediately after recovery
pytest backend/tests/ -x
```
