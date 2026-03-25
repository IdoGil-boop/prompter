<!-- managed by claude-code-starter -->
# Instinct Learning System

This directory stores learned behaviors ("instincts") — small, atomic patterns with confidence scoring that accumulate over sessions.

## Structure

```
instincts/
  personal/           # Auto-discovered from your sessions
  inherited/          # Imported from teammates or other sources
  evolved/            # Higher-level artifacts generated from clusters
    agents/           # Multi-step process agents
    skills/           # Auto-triggered behavior skills
    commands/         # User-invoked action commands
```

## How It Works

1. **Observation**: PostToolUse hooks log tool patterns to `.observations.jsonl`
2. **Analysis**: SessionEnd hook analyzes patterns, writes `.pattern_summary.json`
3. **Creation**: `/maintain` reviews patterns and creates instinct YAML files
4. **Evolution**: `/instinct-evolve` clusters 3+ related instincts into skills/commands

## Commands

| Command | Purpose |
|---------|---------|
| `/instinct-status` | Show all instincts by domain |
| `/instinct-import` | Import from files/URLs |
| `/instinct-export` | Export for sharing |
| `/instinct-evolve` | Cluster into skills/commands |

See `.claude/skills/instinct-learning/SKILL.md` for full documentation.
