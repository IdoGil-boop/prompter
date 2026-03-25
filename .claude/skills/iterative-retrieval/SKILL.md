<!-- managed by claude-code-starter -->
---
name: iterative-retrieval
description: Pattern for progressively refining context retrieval in sub-agent and multi-step workflows
version: 1.0.0
---

# Iterative Retrieval Pattern

Solves the "context problem" in multi-agent workflows where the agent doesn't know what context it needs until it starts working.

## 4-Phase Loop

```
DISPATCH ----> EVALUATE
   ^               |
   |               v
  LOOP <------ REFINE

Max 3 cycles, then proceed with best available context
```

### Phase 1: DISPATCH
Start broad — glob patterns, keyword searches, exclude obvious non-matches.

### Phase 2: EVALUATE
Score each file for relevance (0-1.0). Identify gaps and new search terms.

### Phase 3: REFINE
Add new patterns from high-relevance files. Adopt codebase terminology. Exclude confirmed irrelevant paths.

### Phase 4: LOOP
- 3+ high-relevance files AND no critical gaps? → Stop
- Reached cycle 3? → Stop with best available
- Otherwise → Back to DISPATCH

## Best Practices

1. Start broad, narrow progressively
2. Learn codebase terminology in cycle 1
3. Track gaps explicitly
4. Stop at "good enough" — 3 high-relevance files beats 10 mediocre ones
5. Respect the 3-cycle limit
