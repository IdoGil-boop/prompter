<!-- managed by claude-code-starter -->
---
name: instinct-learning
description: Instinct-based learning system that observes sessions, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents.
version: 2.0.0
---

# Instinct Learning System

Turns Claude Code sessions into reusable knowledge through atomic "instincts" — small learned behaviors with confidence scoring that accumulate over time.

## Core Concept

An **instinct** is the smallest unit of learned behavior:
- **Atomic**: one trigger, one action
- **Confidence-weighted**: 0.3 (tentative) through 0.9 (near-certain)
- **Domain-tagged**: code-style, testing, git, debugging, workflow, architecture
- **Evidence-backed**: tracks observations that created/reinforced it

Stored as YAML files in `.claude/instincts/`.

## Instinct YAML Format

```yaml
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
created: "2026-01-15"
last_reinforced: "2026-01-15"
observations: 5
---

# Prefer Functional Style

## Action
Use functional patterns over classes when appropriate.

## Evidence
- Observed 5 instances of functional pattern preference
- User corrected class-based approach to functional
```

## Confidence Scoring

| Score | Label | Behavior |
|-------|-------|----------|
| 0.3 | Tentative | Suggested, not enforced |
| 0.5 | Moderate | Applied when clearly relevant |
| 0.7 | Strong | Auto-approved, applied by default |
| 0.9 | Near-certain | Core behavior, always applied |

### Adjustments
- Pattern observed again: +0.1 (cap 0.9)
- User doesn't correct: +0.05 passive
- User explicitly corrects: -0.2
- Contradicting evidence: -0.1

## Directory Structure

```
.claude/instincts/
  personal/           # Auto-discovered from sessions
  inherited/          # Imported from teammates
  evolved/            # Higher-level artifacts from clusters
    agents/
    skills/
    commands/
```

## Evolution

When 3+ related instincts accumulate, `/instinct-evolve` clusters them into commands, skills, or agents in `.claude/instincts/evolved/`.

## Commands

| Command | Purpose |
|---------|---------|
| `/instinct-status` | Show all instincts by domain + confidence |
| `/instinct-import` | Import instincts from YAML files or URLs |
| `/instinct-export` | Export instincts as shareable YAML |
| `/instinct-evolve` | Cluster 3+ related instincts into skills/commands |
