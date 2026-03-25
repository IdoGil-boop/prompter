<!-- managed by claude-code-starter -->
---
description: Import instincts from files, URLs, or teammates
---

# Instinct Import

Import instinct YAML files into `.claude/instincts/inherited/`.

## Usage

```
/instinct-import path/to/instincts.yaml
/instinct-import https://example.com/instincts.yaml
```

## Steps

1. Read the source file/URL
2. Validate YAML format (id, trigger, confidence, domain required)
3. Add `imported_from` and `imported_at` metadata
4. Save to `.claude/instincts/inherited/`
5. Report what was imported
