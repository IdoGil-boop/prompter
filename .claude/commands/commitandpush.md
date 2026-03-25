<!-- managed by claude-code-starter -->
---
description: Stage, commit, push as branch, open PR, verify CI passes
---

# Commit and Push

## Default Behavior

Unless the user specifies otherwise, this command:
1. Creates a feature branch from the current changes
2. Pushes and **opens a PR immediately** (the PR is required — CI checks run against it)
3. Monitors CI via `gh pr checks`
4. On failure: identifies the root pattern, fixes it **globally** across the codebase, re-pushes
5. Repeats the CI loop until green or 3 attempts exhausted

## Steps

### 1. Stage & Commit
1. `git add` all relevant saved changes (never `git add .`)
2. `git diff --cached --stat` to review what's staged
3. `git commit` with conventional commit message

### 2. Branch & Push
1. If on `main`/`master`, create a branch: `git checkout -b feat/<short-description>` (or `fix/`, `chore/` etc. based on commit type)
2. `git push -u origin HEAD`

### 3. Open PR (mandatory — enables CI loop)
1. `gh pr create --title "<commit message>" --body "<summary of changes with test plan>"`
2. Print the PR URL
3. Store the PR number for subsequent CI checks

This step is **not optional**. The PR must exist before entering the CI loop because `gh pr checks` is the mechanism for monitoring workflow status.

### 4. CI Loop (up to 3 iterations)

Repeat:

#### 4a. Wait for CI
1. `gh pr checks <pr-number> --watch --fail-level all`
2. If all checks pass → **done**, print success and exit loop

#### 4b. Diagnose Failure
1. Identify the failed run: `gh run list --branch <branch> --limit 1 --json databaseId,status,conclusion`
2. Get failure details: `gh run view <run-id> --log-failed`
3. Read the error output carefully and identify the **root pattern** (not just the single broken line)

#### 4c. Fix Pattern Globally
1. Identify the anti-pattern (e.g., wrong import path, missing type annotation, deprecated API usage)
2. **Grep the entire codebase** for all instances of the same pattern — never fix just one occurrence
3. Fix every instance found
4. Run the relevant linter/type-checker/test locally if possible to verify before pushing

#### 4d. Push Fix
1. `git add` the changed files (never `git add .`)
2. `git commit -m "fix: resolve CI failure — <pattern description> (globally)"`
3. `git push`
4. Return to step 4a

If still failing after 3 iterations, post a PR comment explaining the blocker and notify the user.

## Rules

- Never commit `.env`, credentials, or build artifacts
- Use conventional commit format: `type: description`
- One logical change per commit (use `/commit-by-feature` for multiple)
- Ask before force-pushing
- If the user says "push to main" or "push directly", skip the branch/PR flow
- If the user specifies a branch name, use that instead of auto-generating one
- The PR **must** be opened before checking CI — do not attempt to monitor CI without a PR
