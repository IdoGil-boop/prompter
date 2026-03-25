<!-- managed by claude-code-starter -->
---
name: repo-explorer
description: Quickly map a repository's structure, key entry points, and architecture.
---

# Repo Explorer

## When to Use

- First time working in a new area of the codebase
- Need to understand how modules connect
- Looking for where specific logic lives

## Workflow

### Step 1 — Map the structure
```bash
find . -type f -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" | head -50
```

### Step 2 — Find entry points
Look for: main files, route definitions, task registrations, CLI entry points.

### Step 3 — Identify key nodes
For each major directory:
- What is its responsibility?
- What does it export?
- What does it depend on?

### Step 4 — Map connections
```bash
# Find imports/requires between modules
grep -rn "from\|import\|require" backend/app/ | head -30
```

## Output Format

```
## Architecture Map

### Entry Points
- backend/main.py — API server
- backend/worker.py — Background tasks

### Key Modules
- backend/app/models/ — Data models
- backend/app/routes/ — API endpoints
- backend/app/services/ — Business logic
```
