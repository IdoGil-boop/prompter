<!-- managed by claude-code-starter -->
---
description: Export instincts as YAML for sharing with teammates
---

# Instinct Export

Export instincts from `.claude/instincts/` as shareable YAML.

## Steps

1. Read all instinct files
2. Strip private data (file paths, project names, session data)
3. Filter by confidence >= 0.5 (skip tentative instincts)
4. Output as clean YAML
5. Optionally filter by domain

## Privacy

- Only abstract patterns are exported, never raw code
- File paths and project names are stripped
- Session data is removed
