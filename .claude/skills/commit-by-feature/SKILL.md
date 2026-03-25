<!-- managed by claude-code-starter -->
---
name: commit-by-feature
description: Groups all unstaged/untracked git changes by logical domain and commits them as separate, well-described commits.
---

# Commit by Feature

Splits a large unstaged batch into logical commits — one per feature/domain.

## When to Use

- After a multi-phase session with many changed files
- When `git status` shows 10+ files across unrelated domains
- Before creating a PR — clean history makes review easier

## Workflow

### Step 1 — Survey
Run `git status --short` and `git diff --stat HEAD`.

### Step 2 — Group by Domain

| Domain | Commit type |
|--------|-------------|
| Backend API / routes | `feat:` or `fix:` |
| Frontend components | `feat:` or `fix:` |
| Tests | `test:` |
| Docs / plans | `docs:` |
| Dependencies | `chore:` |
| CI / infra | `ci:` or `chore:` |
| Deletions / cleanup | `chore:` |

### Step 3 — Stage and Commit Each Group
```bash
git add <file1> <file2>
git commit -m "type: short description"
```

### Step 4 — Verify Clean State
```bash
git status --short
git log --oneline -10
```

## Rules

- **Never `git add .`** — risks committing secrets or build artifacts
- **One logical change per commit**
- **Deletions deserve their own commit**
- **Dependency bumps alone**
