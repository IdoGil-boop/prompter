<!-- managed by claude-code-starter -->
---
description: Show all learned instincts grouped by domain with confidence levels
---

# Instinct Status

Show all instincts from `.claude/instincts/` grouped by domain.

## Steps

1. Read all YAML files in `.claude/instincts/personal/`, `inherited/`, `evolved/`
2. Parse frontmatter for id, trigger, confidence, domain, observations
3. Group by domain, sort by confidence (highest first)
4. Display summary table

## Output Format

```
## code-style (3 instincts)
| ID | Confidence | Trigger | Observations |
|----|-----------|---------|-------------|
| prefer-functional | 0.7 Strong | when writing new functions | 5 |
```
