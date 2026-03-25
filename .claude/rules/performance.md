<!-- managed by claude-code-starter -->
# Performance Optimization

## Model Selection Strategy

**Haiku** (lightweight, cost-effective):
- Lightweight agents with frequent invocation
- Pair programming and iterative code generation
- Worker agents in multi-agent systems
- Quick formatting, linting, and simple refactors

**Sonnet** (best coding model — use for 90% of work):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks and debugging
- Code review and refactoring

**Opus** (deepest reasoning):
- Complex architectural decisions
- Security reviews and threat modeling
- Cross-cutting concerns spanning many files
- Research and analysis tasks

## Context Window Management

**Avoid last 20% of context** for:
- Large-scale refactoring (multiple files)
- Feature implementation spanning many modules
- Debugging complex interactions
- Migration generation (needs full model context)

**Lower context sensitivity** (safe near limits):
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes in isolated functions

## Ultrathink + Plan Mode

For complex tasks requiring deep reasoning:
1. Use `ultrathink` for enhanced thinking
2. Enable **Plan Mode** for structured approach
3. "Rev the engine" with multiple critique rounds
4. Use split-role sub-agents for diverse analysis

## Troubleshooting Failures

If tests or build fail:
1. Read the full error traceback
2. Check for missing migrations
3. Verify fixture/test setup
4. Fix incrementally, verify after each fix
