# prompter

[![CI](https://github.com/yourusername/prompter/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/prompter/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Autoresearch-style optimizer for LLM agent systems. Iteratively improves agent configurations (system prompts, tools, RAG, context, memory) by evaluating against user-provided test suites.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/nanochat) approach: instead of tuning `train.py` for `val_bpb`, prompter tunes an agent config (prompts, tools, architecture) against a user-defined test suite.

## Quick Start

```bash
# Install
pip install prompter
# or from source:
uv sync --group dev

# Optimize an agent
prompter optimize ./examples/sentiment-classifier/agent \
    ./examples/sentiment-classifier/tests.yaml \
    --max-iters 10 --model gpt-4o-mini

# Evaluate without optimizing
prompter evaluate ./examples/sentiment-classifier/agent \
    ./examples/sentiment-classifier/tests.yaml

# View optimization history
prompter history ./optimized/history.jsonl
```

## How It Works

```
                    ┌─────────────────────────────────────────┐
                    │          OPTIMIZATION LOOP               │
                    │                                          │
  ┌──────────┐     │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
  │  Agent   │─────│─>│ Evaluate │─>│ Analyze  │─>│Propose │ │
  │  Config  │     │  │ vs Tests │  │ Failures │  │Mutation│ │
  └──────────┘     │  └──────────┘  └──────────┘  └───┬────┘ │
       ^           │       ^                           │      │
       │           │       │    ┌──────────┐           v      │
       └───────────│───────│────│ Keep or  │<────┌─────────┐  │
                   │       │    │ Revert   │     │  Apply  │  │
                   │       │    └──────────┘     │Mutation │  │
                   │       │                     └─────────┘  │
                   │       └──────────────────────────┘       │
                   └──────────────────────────────────────────┘

  Mutation Types (escalation ladder):
    Tier 1: Prompt rewrite (cheap, fast)
    Tier 2: Tool description edits
    Tier 3: Config value adjustments
    Tier 4: Tool implementation rewrites
    Tier 5: Add/remove tools
    Tier 6: Architecture mutations (RAG, context, memory)
```

### The Loop

1. **Evaluate**: Run agent against test suite, compute scores with variance tracking
2. **Analyze**: Identify failing test cases; attribution matrix pinpoints suspect components
3. **Propose**: LLM-driven mutation proposal targeting failures (guided by attribution)
4. **Apply**: Execute mutation (prompt rewrite, tool change, architecture mutation)
5. **Re-evaluate**: Score the mutated config (multi-run for statistical confidence)
6. **Keep/Revert**: Accept if effective_score improves (mean - lambda * variance)

### Key Mechanisms

- **Mock-First Discovery**: Before building expensive infrastructure, mock the capability. If the mock improves score, build the real thing. The mock output becomes the optimization target.
- **Component Attribution**: Trace-based lightweight attribution every iteration + periodic ablation sweeps for ground truth. Guides mutations toward failing components.
- **Model Escalation**: Validate mutations across model tiers (local -> cheap -> SOTA) for cost control.
- **Variance Hardening**: effective_score = mean - lambda * variance prevents accepting flaky improvements.

## Features

- **9 mutation types**: prompt rewrite, tool description, tool implementation, config values, add/remove tools, RAG/context/memory architecture mutations
- **Statistical rigor**: Bootstrap CI, multi-run variance tracking, effective score penalty
- **Mock-first optimization**: Test hypotheses cheaply before building
- **Attribution-guided search**: Trace + ablation attribution pinpoints failing components
- **Cost-efficient**: Escalation ladder (cheap mutations first), model tier validation
- **Rich CLI**: Colored output, score sparklines, prompt diffs, progress tracking
- **Config file support**: `prompter.yaml` for persistent configuration
- **Extensible**: Plugin any LLM via the `LLMAdapter` protocol (OpenAI, Ollama, etc.)

## Architecture

```
src/prompter/
├── config/          # AgentConfig (immutable), snapshots, config file support
├── eval/            # Evaluator, metrics, bootstrap CI, variance tracking
├── llm/             # LLMAdapter protocol, OpenAI/Ollama adapters, escalation
├── mutations/       # 9 typed mutation operators, proposer, escalation ladder
├── runner/          # AgentRunner + ToolSandbox (sandboxed tool execution)
├── history/         # Append-only JSONL history store + analysis
├── attribution/     # Trace-based + ablation attribution matrix
├── mock/            # Mock-first engine + target optimization
├── optimizer.py     # Main optimization loop
└── cli.py           # Rich CLI entry point
```

## CLI Reference

```bash
# Basic optimization
prompter optimize <agent_dir> <test_suite> [options]

# Options:
#   --max-iters N          Maximum iterations (default: 20)
#   --target-score F       Stop when score reaches F (default: 1.0)
#   --model MODEL          LLM model (default: gpt-4o-mini)
#   --base-url URL         LLM API base URL
#   --api-key KEY          API key (or set OPENAI_API_KEY)
#   --n-runs N             Eval runs per iteration (default: 3)
#   --output-dir DIR       Where to save results
#   --variance-modes MODES Comma-separated: run,order,paraphrase
#   --tiers TIERS          Model tiers: name:provider:model,...
#   --config FILE          Load from prompter.yaml
#   --verbose              Detailed output

# Evaluate only
prompter evaluate <agent_dir> <test_suite>

# View history
prompter history <history_file>
```

## Configuration File

Create a `prompter.yaml` for persistent settings:

```yaml
agent_dir: ./my-agent
test_suite: ./tests.yaml
optimizer:
  max_iterations: 30
  target_score: 0.95
  n_eval_runs: 5
  variance_modes: [run, order]
llm:
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
tiers:
  local: {model: llama3.2, provider: ollama}
  cheap: {model: gpt-4o-mini, provider: openai}
  sota: {model: gpt-4o, provider: openai}
```

```bash
prompter optimize ./agent ./tests.yaml --config prompter.yaml
# CLI args override config file values
```

## Examples

| Example | Description |
|---------|-------------|
| `examples/sentiment-classifier/` | Basic prompt optimization (15 test cases) |
| `examples/calculator-agent/` | Tool-using agent with calculator |
| `examples/rag-qa-agent/` | Question answering with context (mock-first RAG) |
| `examples/customer-support/` | Multi-tool support agent (7 test cases) |

## Writing Test Suites

```yaml
tests:
  - id: greeting
    input: "Say hello"
    expected: "hello"
    eval_mode: exact_match    # exact_match | contains | semantic | custom

  - id: sentiment
    input: "I love this product!"
    expected: "POSITIVE"
    eval_mode: exact_match
    weight: 2.0               # Higher weight = more important

  - id: knowledge
    input: "What is the capital of France?"
    expected: "Paris"
    eval_mode: contains
    tags: [knowledge, geography]
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/prompter/

# Type check
uv run mypy src/prompter/ --ignore-missing-imports

# All checks
make check
```

## License

MIT
