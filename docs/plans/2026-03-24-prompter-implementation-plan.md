# Implementation Plan: prompter

**Date**: 2026-03-24
**Status**: Active
**Author**: Planning Agent

---

## Overview

Prompter applies Karpathy's autoresearch concept to LLM agent optimization. Instead of tuning `train.py` for `val_bpb`, it iteratively optimizes an agent config (system prompts, tools, RAG, context, memory) against a user-provided test suite. The optimizer loop is: **evaluate → analyze failures → propose mutation → apply → re-evaluate → keep/revert**, one mutation per iteration for clean attribution.
twitt: https://x.com/karpathy/status/2031135152349524125
repo: https://github.com/karpathy/nanochat/commit/6ed7d1d82cee16c2e26f45d559ad3338447a6c1b
This plan is phased so that each phase produces a working, demo-able artifact. Phase 1 (MVP) is a prompt-only optimizer that can demonstrably improve a system prompt. Subsequent phases add tool mutations, the mock-first mechanism, attribution, and architecture-level optimization.

---

## Inventory: What Exists vs. What's Needed

### Exists (✅)

| Module | Key Types | Status |
|--------|-----------|--------|
| `config/agent_config.py` | `AgentConfig`, `ToolSpec` | Complete — load/save/diff/snapshot/hash, immutable with `with_*` builders |
| `config/snapshot.py` | `ConfigSnapshot` | Complete — create/save/load with metadata |
| `eval/test_suite.py` | `TestCase`, `TestSuite` | Complete — YAML loader, tag filtering, weights |
| `eval/metrics.py` | `exact_match`, `semantic_similarity`, `tool_call_match`, `custom_fn` | Complete — registry-based dispatch via `score_output()` |
| `eval/bootstrap.py` | `BootstrapResult`, `bootstrap_ci`, `bootstrap_delta` | Complete |
| `eval/variance.py` | `VarianceReport`, `VarianceTracker`, `effective_score` | Complete |
| `eval/evaluator.py` | `Evaluator`, `EvalReport`, `TestResult`, `TraceEvent`, `AgentFn` | Complete — async eval with optional CI/variance |
| `llm/adapter.py` | `LLMAdapter` (Protocol), `Message`, `ToolCall`, `ToolDefinition`, `TokenUsage`, `LLMResponse` | Complete |
| `llm/openai_compat.py` | `OpenAICompatAdapter` | Complete — supports any OpenAI-compatible API |
| `llm/ollama.py` | `OllamaAdapter` | Complete — local Ollama |
| `llm/escalation.py` | `ModelEscalation`, `EscalationResult`, `EscalationEvalFn` | Complete — tiered validation with early exit |
| `mutations/base.py` | `Mutation` (ABC), `MutationResult`, `MutationProposal`, `MutationContext`, registry | Complete |
| `mutations/prompt.py` | `SystemPromptMutation` | Complete — LLM-driven prompt rewrite |
| `mutations/ladder.py` | `LadderState`, `ESCALATION_TIERS` | Complete — tier tracking with auto-escalation |
| `mutations/proposer.py` | `MutationProposer`, `_parse_proposal` | Complete — LLM-driven failure analysis → proposal |
| `history/store.py` | `HistoryStore`, `IterationRecord` | Complete — append-only JSONL |
| `pyproject.toml` | — | Complete — deps, scripts, tool config |
| `Makefile` | — | Complete — install/test/lint/typecheck/check/clean |

### Needs Building (🔲)

| Module | Priority | Phase |
|--------|----------|-------|
| `runner/agent_runner.py` | **Critical** | 1 |
| `optimizer.py` | **Critical** | 1 |
| `cli.py` | **Critical** | 1 |
| Tests for Phase 0 code | **Critical** | 1 |
| Example project | **Critical** | 1 |
| `mutations/tool_desc.py` | High | 2 |
| `mutations/config_value.py` | High | 2 |
| `mutations/tool_impl.py` | High | 2 |
| `mutations/architecture.py` | Medium | 4 |
| `runner/tool_sandbox.py` | High | 2 |
| `history/analysis.py` | Medium | 3 |
| `mock/engine.py` | Medium | 4 |
| `mock/target.py` | Medium | 4 |
| `attribution/tracer.py` | Medium | 3 |
| `attribution/ablation.py` | Medium | 3 |
| `attribution/matrix.py` | Medium | 3 |
| `README.md` | High | 1 |

---

## Phase 1: MVP — Prompt-Only Optimization Loop

**Goal**: A working CLI that takes an agent config directory + test suite YAML, runs the optimize loop, and demonstrably improves a system prompt. Prompt-only mutations (Tier 1). No tools, no RAG, no mock, no attribution.

**Demo**: `prompter optimize ./my-agent ./tests.yaml --max-iters 10` → system prompt improves from 40% to 85% on test suite.

### Step 1.1: Agent Runner (`src/prompter/runner/agent_runner.py`)

The missing link between `AgentConfig` and `Evaluator`. Converts a config into the `AgentFn` callable that the evaluator expects.

```python
# Key interface
class AgentRunner:
    """Wraps an AgentConfig + LLMAdapter into the AgentFn protocol."""

    def __init__(self, config: AgentConfig, llm: LLMAdapter): ...

    async def run(self, input: str, context: dict | None = None) -> str:
        """Send input through the agent config and return output."""

    def as_agent_fn(self) -> AgentFn:
        """Return a callable matching the AgentFn protocol."""
```

**Implementation details**:
- Constructs `messages` list: system message from `config.system_prompt`, user message from input
- If `config.tools` exist and the LLM supports tools, includes `ToolDefinition` list (Phase 2 adds execution)
- For Phase 1, tools are description-only — the LLM sees them but can't execute them
- Returns `response.content` as the agent output
- Stores trace events for later attribution (list of `TraceEvent`)

**Complexity**: Low
**Risk**: Low — straightforward adapter pattern
**File**: `src/prompter/runner/__init__.py`, `src/prompter/runner/agent_runner.py`

### Step 1.2: Optimizer Core (`src/prompter/optimizer.py`)

The main optimization loop. This is the heart of the system.

```python
@dataclass
class OptimizerConfig:
    max_iterations: int = 20
    target_score: float = 1.0
    n_eval_runs: int = 3
    compute_ci: bool = True
    variance_lambda: float = 0.1
    improvement_threshold: float = 0.01
    snapshots_dir: Path | None = None

class Optimizer:
    def __init__(
        self,
        config: AgentConfig,
        test_suite: TestSuite,
        llm: LLMAdapter,
        optimizer_llm: LLMAdapter | None = None,
        opt_config: OptimizerConfig = OptimizerConfig(),
        history: HistoryStore | None = None,
    ): ...

    async def run(self) -> OptimizationResult:
        """Main loop: evaluate → propose → apply → re-evaluate → keep/revert."""

    async def _iteration(self, iteration: int) -> IterationOutcome: ...
```

**Loop pseudocode**:
```
1. baseline_report = evaluate(current_config)
2. record baseline in history
3. for i in range(max_iterations):
   a. if baseline_report.aggregate_score >= target_score: break (success)
   b. context = MutationContext(config, eval_report, history, attribution_hints={})
   c. proposal = proposer.propose(context, ladder)
   d. mutation = registry[proposal.mutation_type](llm)
   e. mutation_result = mutation.apply(context, proposal)
   f. candidate_report = evaluate(mutation_result.config)
   g. delta = candidate_report.aggregate_score - current_score
   h. if compute_ci: run bootstrap_delta for statistical significance
   i. if delta >= improvement_threshold (and CI significant):
        accept: current_config = mutation_result.config, update score
        ladder.record_result(tier, accepted=True)
      else:
        revert: keep current_config
        ladder.record_result(tier, accepted=False)
        if ladder.should_escalate(tier): ladder.escalate()
   j. record iteration in history
   k. optionally save snapshot
4. return OptimizationResult(best_config, history, final_report)
```

**Key design decisions**:
- `optimizer_llm` defaults to the same LLM but can be a cheaper model for the proposer/mutator
- The optimizer owns the `Evaluator`, `MutationProposer`, `LadderState`, and `HistoryStore`
- `AgentRunner` is created fresh each iteration with the candidate config
- Rich progress output via `rich.progress` and `rich.console`

**Complexity**: Medium — many moving parts but each is already built
**Risk**: Medium — integration of all components; careful error handling needed
**Dependencies**: Steps 1.1
**File**: `src/prompter/optimizer.py`

### Step 1.3: CLI Entry Point (`src/prompter/cli.py`)

```python
@click.group()
def main(): ...

@main.command()
@click.argument("agent_dir", type=click.Path(exists=True))
@click.argument("test_suite", type=click.Path(exists=True))
@click.option("--max-iters", default=20)
@click.option("--target-score", default=1.0)
@click.option("--model", default="gpt-4o-mini")
@click.option("--base-url", default="https://api.openai.com/v1")
@click.option("--api-key", envvar="OPENAI_API_KEY")
@click.option("--n-runs", default=3, help="Eval runs per iteration for variance")
@click.option("--output-dir", default=None, help="Where to save optimized config")
@click.option("--verbose", is_flag=True)
async def optimize(...): ...

@main.command()
@click.argument("agent_dir", type=click.Path(exists=True))
@click.argument("test_suite", type=click.Path(exists=True))
@click.option("--model", default="gpt-4o-mini")
async def evaluate(...):
    """Run test suite against config without optimizing."""

@main.command()
@click.argument("history_file", type=click.Path(exists=True))
def history(...):
    """Print optimization history summary."""
```

**Rich output includes**:
- Progress bar with iteration count
- Live table: iteration | mutation type | score before → after | delta | status
- Final summary: best score, iterations taken, total tokens used
- `--verbose` shows full mutation descriptions and failure details

**Complexity**: Low
**Risk**: Low — click + rich are well-trodden
**Dependencies**: Step 1.2
**File**: `src/prompter/cli.py`

### Step 1.4: Tests for All Phase 0 + Phase 1 Code

**Test structure**:
```
tests/
├── conftest.py              # shared fixtures: mock LLM, sample configs, sample test suites
├── config/
│   ├── test_agent_config.py # load/save/diff/hash/with_* round-trips
│   └── test_snapshot.py     # create/save/load
├── eval/
│   ├── test_metrics.py      # each metric function, edge cases
│   ├── test_bootstrap.py    # CI computation, empty array, single value
│   ├── test_variance.py     # run variance, effective_score
│   ├── test_evaluator.py    # full eval with mock agent_fn
│   └── test_test_suite.py   # YAML loading, filtering, weights
├── llm/
│   ├── test_adapter.py      # protocol conformance checks
│   ├── test_escalation.py   # tier progression, early exit, acceptance
│   └── test_openai_compat.py # response parsing (mock httpx)
├── mutations/
│   ├── test_base.py         # registry, mutation protocol
│   ├── test_prompt.py       # prompt mutation with mock LLM
│   ├── test_ladder.py       # escalation logic, consecutive failures
│   └── test_proposer.py     # proposal parsing, type validation
├── history/
│   └── test_store.py        # append/load/get_best/JSONL round-trip
├── runner/
│   └── test_agent_runner.py # AgentRunner with mock LLM
└── test_optimizer.py        # integration: full loop with mock LLM, verify score improves
```

**Key testing patterns**:

1. **Mock LLM fixture** — a deterministic `LLMAdapter` that returns canned responses based on input patterns. This is the most critical fixture because it allows testing the entire loop without API calls.

```python
class MockLLM:
    """Returns predefined responses. Tracks all calls for assertion."""

    def __init__(self, responses: list[str] | Callable[[list[Message]], str]):
        self._responses = responses
        self._call_log: list[list[Message]] = []

    async def complete(self, messages, tools=None, **kw) -> LLMResponse:
        self._call_log.append(messages)
        if callable(self._responses):
            content = self._responses(messages)
        else:
            content = self._responses.pop(0)
        return LLMResponse(content=content, usage=TokenUsage(10, 10))

    @property
    def model_id(self) -> str: return "mock"

    @property
    def tier(self) -> str: return "local"
```

2. **Sample agent config fixture** — a minimal config directory with a deliberately bad system prompt that the optimizer can improve.

3. **Sample test suite fixture** — 5-10 test cases with known-good expected outputs.

4. **Integration test** (`test_optimizer.py`): Wire up MockLLM → AgentRunner → Evaluator → Optimizer. The mock LLM returns better responses when the system prompt contains certain keywords. Verify the optimizer discovers those keywords within N iterations.

**Coverage target**: 80%+ for all modules.

**Complexity**: Medium — lots of files but each test is straightforward
**Risk**: Low
**Dependencies**: Steps 1.1–1.3
**File**: `tests/` directory tree

### Step 1.5: Example Project

```
examples/
└── sentiment-classifier/
    ├── agent/
    │   └── system_prompt.md    # "You are a sentiment classifier. Reply POSITIVE or NEGATIVE."
    ├── tests.yaml              # 15 labeled I/O pairs
    └── README.md               # How to run this example
```

The system prompt starts deliberately vague. The optimizer should add specificity (handling edge cases, format instructions, etc.) and improve accuracy.

**Complexity**: Low
**Risk**: Low
**Dependencies**: Step 1.3

### Step 1.6: README.md

Project README with: what it is, how it works (loop diagram in ASCII), quick start, example output, architecture overview, contributing.

**Complexity**: Low
**Risk**: Low
**Dependencies**: Step 1.5

### Phase 1 — Milestone Checklist

- [ ] `prompter optimize` runs end-to-end with a real LLM
- [ ] `prompter evaluate` shows baseline score
- [ ] `prompter history` shows iteration log
- [ ] Example project demonstrates improvement
- [ ] All Phase 0 code has tests at 80%+ coverage
- [ ] Integration test passes with mock LLM
- [ ] README is complete

---

## Phase 2: Tool Mutations + Sandbox

**Goal**: The optimizer can modify tool descriptions, tool implementations, config values, and add/remove tools. Tool calls are executed in a sandboxed subprocess.

### Step 2.1: Tool Sandbox (`src/prompter/runner/tool_sandbox.py`)

Executes tool implementations in an isolated subprocess with timeout and resource limits.

```python
class ToolSandbox:
    """Executes tool code in a subprocess with timeout."""

    def __init__(self, timeout_seconds: float = 30.0, allowed_modules: list[str] | None = None): ...

    async def execute(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> str:
        """Run tool implementation with given arguments, return string result."""
```

**Implementation details**:
- Tool implementation code is written to a temp file
- Executed via `asyncio.create_subprocess_exec` with `python -c`
- Stdin receives JSON arguments, stdout captures result
- Hard timeout via `process.wait(timeout=...)`
- Optional module allowlist via `--allowed-modules` to restrict imports
- Returns stdout as string; stderr is logged but not returned to agent

**Security considerations**:
- Subprocess isolation (not in-process `exec`)
- Timeout enforcement
- No network access by default (future: network namespace)
- No filesystem writes outside temp dir (future: seccomp/landlock)
- For MVP, document the risk and recommend running in a container

**Complexity**: Medium
**Risk**: Medium — subprocess management, security boundaries
**File**: `src/prompter/runner/tool_sandbox.py`

### Step 2.2: Enhanced Agent Runner

Update `AgentRunner` to handle the tool call → tool result → continuation loop:

```python
async def run(self, input: str, context: dict | None = None) -> str:
    messages = [system_msg, user_msg]
    for _ in range(max_tool_rounds):
        response = await self.llm.complete(messages, tools=tool_defs)
        if not response.tool_calls:
            return response.content
        for tc in response.tool_calls:
            result = await self.sandbox.execute(self.config.tools[tc.name], tc.arguments)
            messages.append(Message(role="tool", content=result, tool_call_id=tc.id))
    return messages[-1].content  # fallback after max rounds
```

**Complexity**: Medium
**Risk**: Low — standard agentic loop pattern
**Dependencies**: Step 2.1

### Step 2.3: Tool Description Mutation (`src/prompter/mutations/tool_desc.py`)

```python
@register_mutation
class ToolDescriptionMutation(Mutation):
    type_id = "tool_desc.edit"
    cost_tier = 2

    async def apply(self, context, proposal) -> MutationResult:
        # LLM rewrites tool description based on failure analysis
        # Uses config.with_tool() to create new config
```

Targets cases where the LLM doesn't call the right tool or passes wrong arguments because the description is misleading.

**Complexity**: Low — follows same pattern as `SystemPromptMutation`
**Risk**: Low

### Step 2.4: Config Value Mutation (`src/prompter/mutations/config_value.py`)

```python
@register_mutation
class ConfigValueMutation(Mutation):
    type_id = "config.adjust"
    cost_tier = 3

    async def apply(self, context, proposal) -> MutationResult:
        # Adjusts values in rag_config, context_strategy, or memory_strategy
```

**Complexity**: Low
**Risk**: Low

### Step 2.5: Tool Implementation Mutation (`src/prompter/mutations/tool_impl.py`)

```python
@register_mutation
class ToolImplementationMutation(Mutation):
    type_id = "tool_impl.modify"
    cost_tier = 4

    async def apply(self, context, proposal) -> MutationResult:
        # LLM rewrites tool implementation code
        # Sandbox-validates before accepting (syntax check + smoke test)
```

This is the first mutation that generates executable code. Safety: the sandbox validates the new implementation can at least import and run without errors before accepting.

**Complexity**: Medium
**Risk**: Medium — LLM-generated code needs validation

### Step 2.6: Add/Remove Tool Mutations

```python
@register_mutation
class AddToolMutation(Mutation):
    type_id = "tool.add"
    cost_tier = 5

@register_mutation
class RemoveToolMutation(Mutation):
    type_id = "tool.remove"
    cost_tier = 5
```

**Complexity**: Medium
**Risk**: Medium — adding tools is a bigger search space

### Step 2.7: Tests for Phase 2

- `tests/runner/test_tool_sandbox.py` — timeout, success, error, forbidden module
- `tests/mutations/test_tool_desc.py` — description rewrite with mock LLM
- `tests/mutations/test_config_value.py` — config adjustment
- `tests/mutations/test_tool_impl.py` — implementation rewrite + validation
- `tests/test_optimizer_with_tools.py` — integration test with tool-using agent

### Phase 2 — Milestone Checklist

- [ ] Tool sandbox executes code safely with timeout
- [ ] Agent runner handles multi-turn tool use loop
- [ ] All 5 tool-related mutation operators registered and functional
- [ ] Optimizer can improve a tool-using agent end-to-end
- [ ] Example: calculator agent that needs tool fixes

---

## Phase 3: Attribution + History Analysis

**Goal**: The optimizer can figure out *which components* contribute to failures and target mutations accordingly. Trace-based cheap attribution every iteration; periodic ablation sweeps for ground truth.

### Step 3.1: Trace-Based Attribution (`src/prompter/attribution/tracer.py`)

Lightweight attribution from execution traces already captured by `AgentRunner`.

```python
@dataclass(frozen=True)
class TraceAttribution:
    component_scores: dict[str, float]  # component_name → attribution score

class TraceAttributor:
    """Estimates component contribution from execution traces."""

    def attribute(self, trace: list[TraceEvent], test_result: TestResult) -> TraceAttribution:
        """Which components were active in failing vs. passing tests?"""
```

**Logic**: For each component (system_prompt, tool:X, rag_config), compute how often it appears in failing traces vs. passing traces. Components that appear disproportionately in failures get higher attribution scores.

**Complexity**: Low
**Risk**: Low — heuristic, doesn't need to be perfect

### Step 3.2: Ablation Sweeps (`src/prompter/attribution/ablation.py`)

Ground-truth attribution via component ablation. Expensive, run periodically.

```python
class AblationSweep:
    """Removes one component at a time, measures impact on score."""

    async def run(
        self,
        config: AgentConfig,
        test_suite: TestSuite,
        evaluator: Evaluator,
        llm: LLMAdapter,
    ) -> AblationResult:
        """For each component, create config-without-it, evaluate, compute delta."""
```

**Implementation**: For each component in `config.component_names()`:
- Create ablated config (e.g., `config.without_tool("X")`, or replace system_prompt with generic one)
- Evaluate ablated config
- Delta = original_score - ablated_score
- Positive delta means the component helps; negative means it hurts

**Complexity**: Medium — N+1 evaluations where N = number of components
**Risk**: Low — straightforward concept, expensive to run
**Scheduling**: Run every K iterations (configurable, default K=5), or when optimizer is stuck

### Step 3.3: Attribution Matrix (`src/prompter/attribution/matrix.py`)

Combines trace-based and ablation-based attribution into a unified matrix.

```python
@dataclass
class AttributionMatrix:
    """Component × TestCase attribution scores."""
    matrix: dict[str, dict[str, float]]  # component → test_id → attribution

    def top_suspects(self, n: int = 3) -> list[str]:
        """Components most likely causing failures."""

    def merge_trace(self, trace_attr: TraceAttribution): ...
    def merge_ablation(self, ablation: AblationResult): ...
```

This is fed into `MutationContext.attribution_hints` so the proposer can make targeted suggestions.

**Complexity**: Low
**Risk**: Low

### Step 3.4: History Analysis (`src/prompter/history/analysis.py`)

Deeper analysis over the iteration history for insights.

```python
class HistoryAnalyzer:
    """Extracts patterns from optimization history."""

    def __init__(self, store: HistoryStore): ...

    def stagnation_detector(self) -> bool:
        """True if score hasn't improved in last K iterations."""

    def mutation_effectiveness(self) -> dict[str, float]:
        """Acceptance rate per mutation type."""

    def component_churn(self) -> dict[str, int]:
        """How many times each component has been mutated."""

    def summary(self) -> str:
        """Human-readable optimization summary."""
```

**Complexity**: Low
**Risk**: Low

### Step 3.5: Integrate Attribution into Optimizer

Update `optimizer.py`:
- Create `TraceAttributor` and run after every evaluation
- Run `AblationSweep` every K iterations
- Feed `AttributionMatrix.top_suspects()` into `MutationContext.attribution_hints`
- Use `HistoryAnalyzer.stagnation_detector()` to trigger escalation

### Step 3.6: Tests for Phase 3

- `tests/attribution/test_tracer.py`
- `tests/attribution/test_ablation.py`
- `tests/attribution/test_matrix.py`
- `tests/history/test_analysis.py`

### Phase 3 — Milestone Checklist

- [ ] Trace attribution runs every iteration (cheap)
- [ ] Ablation sweep runs periodically and feeds into proposer
- [ ] History analysis detects stagnation and triggers escalation
- [ ] Mutations become more targeted with attribution hints
- [ ] `prompter history` command shows attribution insights

---

## Phase 4: Mock-First Mechanism + Architecture Mutations

**Goal**: Before building expensive infrastructure (tools, RAG), mock the capability by injecting ideal output. If score improves, build it. The mock artifact becomes the optimization target.

### Step 4.1: Mock Engine (`src/prompter/mock/engine.py`)

```python
@dataclass(frozen=True)
class MockCapability:
    name: str
    description: str
    mock_output_fn: Callable[[str], str] | str
    capability_type: Literal["tool", "rag", "context"]

class MockEngine:
    """Injects mock capabilities into an agent config for hypothesis testing."""

    def inject(self, config: AgentConfig, mock: MockCapability) -> AgentConfig:
        """Create config with the mock capability wired in."""

    async def test_hypothesis(
        self,
        config: AgentConfig,
        mock: MockCapability,
        test_suite: TestSuite,
        evaluator: Evaluator,
        llm: LLMAdapter,
    ) -> MockTestResult:
        """Does adding this mock capability improve the score?"""
```

**How it works**:
1. The proposer suggests "the agent needs access to X" (e.g., a calculator tool, a RAG source)
2. Mock engine creates a `MockCapability` that injects ideal output — e.g., for a calculator tool, it parses the expected output and hardcodes it as the tool result
3. Evaluates the config with the mock injected
4. If score improves significantly → this capability is worth building
5. The mock output becomes the **target label** for the real implementation

### Step 4.2: Mock Target (`src/prompter/mock/target.py`)

```python
@dataclass(frozen=True)
class MockTarget:
    """The target label derived from a successful mock."""
    capability_name: str
    target_outputs: dict[str, str]  # test_id → ideal output from mock
    embedding_targets: list[tuple[str, str]] | None = None  # (query, target_chunk) for RAG

class MockTargetOptimizer:
    """Optimizes a real implementation to match mock targets using embedding similarity."""

    async def optimize_toward_target(
        self, implementation: str, target: MockTarget
    ) -> str:
        """Refine implementation until output matches mock target."""
```

This is "Loop 2" from the architecture: optimize the real implementation (tool code, RAG retrieval) toward the mock artifact using embedding similarity as the loss. This is cheap because it doesn't require the full agent loop — just compare implementation output to target.

### Step 4.3: Architecture Mutations (`src/prompter/mutations/architecture.py`)

```python
@register_mutation
class RAGArchitectureMutation(Mutation):
    type_id = "architecture.rag"
    cost_tier = 6

@register_mutation
class ContextArchitectureMutation(Mutation):
    type_id = "architecture.context"
    cost_tier = 6

@register_mutation
class MemoryArchitectureMutation(Mutation):
    type_id = "architecture.memory"
    cost_tier = 6
```

These are gated by the mock-first mechanism: they only fire after a mock has validated the capability is worth building.

### Step 4.4: Tests for Phase 4

- `tests/mock/test_engine.py` — mock injection, hypothesis testing
- `tests/mock/test_target.py` — target extraction, embedding comparison
- `tests/mutations/test_architecture.py` — RAG/context/memory mutations

### Phase 4 — Milestone Checklist

- [ ] Mock engine can inject hypothetical capabilities
- [ ] Score delta from mock validates whether to build
- [ ] Mock artifacts become optimization targets for real implementations
- [ ] Architecture mutations gated by mock validation
- [ ] Example: agent that needs RAG, discovered and built via mock-first

---

## Phase 5: Model Escalation Integration + Variance Hardening

**Goal**: Multi-tier validation (local → cheap → SOTA) is wired into the optimizer loop. Variance testing is comprehensive.

### Step 5.1: Escalation in Optimizer Loop

Update `optimizer.py` to use `ModelEscalation` when multiple LLM tiers are configured:

```python
# In optimizer._iteration():
if self.escalation:
    escalation_result = await self.escalation.validate(
        eval_fn=lambda adapter: self._evaluate_with(candidate_config, adapter),
        baseline_score=current_score,
    )
    if not escalation_result.accepted:
        # revert
```

### Step 5.2: Comprehensive Variance Testing

Extend `VarianceTracker` and `Evaluator` to support:
- **Order variance**: Shuffle test suite order, measure score variance
- **Condensation variance**: Shorten inputs, measure degradation
- **Paraphrase variance**: Rephrase inputs via LLM, measure consistency

Add CLI flag: `--variance-modes run,order,paraphrase`

### Step 5.3: Effective Score Integration

Wire `effective_score = mean - λ * variance` into the accept/reject decision. A mutation that improves mean but increases variance might be rejected.

### Phase 5 — Milestone Checklist

- [ ] Multi-tier escalation validates mutations across model tiers
- [ ] Bad mutations rejected early at cheap tier
- [ ] Variance-adjusted scoring prevents flaky improvements
- [ ] `--variance-modes` CLI flag works

---

## Phase 6: Polish + Open Source Readiness

**Goal**: The project is portfolio-ready: clean, documented, tested, and impressive.

### Step 6.1: Rich CLI Output

- ASCII art logo on startup
- Animated progress with `rich.live`
- Colored diff view of prompt changes between iterations
- Sparkline of score trajectory
- Token usage and cost estimates

### Step 6.2: Configuration File Support

```yaml
# prompter.yaml
agent_dir: ./my-agent
test_suite: ./tests.yaml
optimizer:
  max_iterations: 30
  target_score: 0.95
  n_eval_runs: 5
llm:
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
tiers:
  local: {model: llama3.2, provider: ollama}
  cheap: {model: gpt-4o-mini, provider: openai}
  sota: {model: gpt-4o, provider: openai}
```

### Step 6.3: Additional Examples

```
examples/
├── sentiment-classifier/   # Phase 1
├── calculator-agent/        # Phase 2 (tool-using)
├── rag-qa-agent/            # Phase 4 (mock-first RAG)
└── customer-support/        # Complex multi-tool agent
```

### Step 6.4: Documentation

- Architecture decision records in `docs/architecture/`
- API reference (auto-generated or hand-written key types)
- Tutorial: "Build your first optimized agent in 10 minutes"

### Step 6.5: CI/CD

- GitHub Actions: lint + typecheck + test on PR
- Coverage badge
- Release workflow with versioned PyPI publish

### Phase 6 — Milestone Checklist

- [ ] README is clear, compelling, and complete
- [ ] 4 example projects covering all phases
- [ ] CI pipeline passes
- [ ] PyPI-installable: `pip install prompter`
- [ ] Documentation covers all key concepts

---

## Key Interfaces Summary

These are the contracts that bind the system together. Changes here ripple everywhere.

### `AgentFn` (Protocol)
```python
async def __call__(self, input: str, context: dict[str, Any] | None = None) -> str
```
Used by: `Evaluator.evaluate()`
Produced by: `AgentRunner.as_agent_fn()`

### `LLMAdapter` (Protocol)
```python
async def complete(messages, tools, temperature, max_tokens) -> LLMResponse
model_id: str
tier: Literal["local", "cheap", "sota"]
```
Used by: `AgentRunner`, `SystemPromptMutation`, `MutationProposer`, `ModelEscalation`

### `Mutation` (ABC)
```python
async def apply(context: MutationContext, proposal: MutationProposal) -> MutationResult
type_id: str
cost_tier: int
```
Registration: `@register_mutation` decorator → `_MUTATION_REGISTRY`

### `EscalationEvalFn` (Protocol)
```python
async def __call__(self, adapter: LLMAdapter) -> float
```
Used by: `ModelEscalation.validate()`

---

## Risks & Mitigations

### Risk 1: LLM API Cost During Development
**Severity**: Medium
**Mitigation**: MockLLM for all tests. Real LLM calls only in examples and manual testing. Track token usage in HistoryStore. Model escalation ensures cheap models filter first.

### Risk 2: Mutation Doesn't Converge
**Severity**: Medium — the optimizer makes random-seeming changes that don't improve score
**Mitigation**: Failure-directed search (proposer sees all failures). History prevents repeating failed mutations. Attribution focuses mutations on guilty components. Escalation ladder expands search space when stuck.

### Risk 3: Tool Sandbox Security
**Severity**: High — LLM-generated code executing on user's machine
**Mitigation**: Subprocess isolation (not `exec`). Timeout enforcement. Document security boundaries prominently. Recommend containerized execution for untrusted configs. Future: seccomp profiles.

### Risk 4: Variance Makes Progress Invisible
**Severity**: Medium — real improvements masked by LLM non-determinism
**Mitigation**: Multiple eval runs per iteration. Bootstrap CI on score deltas. Effective score penalizes variance. Only accept statistically significant improvements.

### Risk 5: Scope Creep
**Severity**: High — project is ambitious for one person
**Mitigation**: Strict phasing. Each phase is independently demo-able. Phase 1 is the minimum viable portfolio piece. Phases 4-6 are nice-to-haves.

### Risk 6: Test Suite Quality
**Severity**: Medium — garbage in, garbage out. Bad test suites produce bad optimizations.
**Mitigation**: Document test suite best practices. Provide `prompter validate-suite` command to check for common issues (too few tests, all same eval mode, no variance in difficulty). Example suites demonstrate good patterns.

---

## Testing Strategy

### Unit Tests
Every module gets a test file. Key patterns:
- **Mock LLM** — deterministic, tracks calls, returns canned responses
- **Temp directories** — `tmp_path` fixture for config/snapshot I/O
- **Parametrize** — test metrics with edge cases (empty string, unicode, long text)
- **Async** — all async functions tested with `pytest-asyncio`

### Integration Tests
- `test_optimizer.py` — full loop with MockLLM, verify score improves
- `test_optimizer_with_tools.py` — tool-using agent optimization
- `test_escalation_integration.py` — multi-tier validation in optimizer

### Manual/E2E Tests
- Run examples against real LLMs
- Verify CLI output formatting
- Check JSONL history files are well-formed

### Coverage
- Target: 80%+ overall, 90%+ for `optimizer.py` and `evaluator.py`
- Measured via `coverage` in Makefile: `make test` → `uv run coverage run -m pytest && uv run coverage report`

---

## Implementation Order (Recommended)

```
Week 1: Phase 1 — MVP
  Day 1-2: Tests for existing Phase 0 code (Step 1.4 partial)
  Day 2-3: AgentRunner (Step 1.1) + its tests
  Day 3-4: Optimizer core (Step 1.2) + its tests
  Day 4-5: CLI (Step 1.3) + example project (Step 1.5)
  Day 5:   README (Step 1.6) + manual end-to-end test

Week 2: Phase 2 — Tool Mutations
  Day 1:   Tool sandbox (Step 2.1)
  Day 2:   Enhanced agent runner (Step 2.2)
  Day 3-4: All mutation operators (Steps 2.3-2.6)
  Day 5:   Integration test + calculator example

Week 3: Phase 3 — Attribution
  Day 1-2: Tracer + ablation (Steps 3.1-3.2)
  Day 3:   Attribution matrix (Step 3.3)
  Day 4:   History analysis (Step 3.4)
  Day 5:   Integration into optimizer (Step 3.5) + tests

Week 4: Phase 4 — Mock-First
  Day 1-2: Mock engine (Step 4.1)
  Day 3:   Mock target optimizer (Step 4.2)
  Day 4:   Architecture mutations (Step 4.3)
  Day 5:   Tests + RAG example

Week 5: Phase 5-6 — Escalation, Variance, Polish
  Day 1-2: Escalation integration + variance hardening
  Day 3-4: CLI polish, config file, additional examples
  Day 5:   Documentation + CI/CD
```

---

## Appendix: File Tree (Target State)

```
src/prompter/
├── __init__.py
├── __main__.py
├── cli.py                        # Phase 1
├── optimizer.py                  # Phase 1
├── config/
│   ├── __init__.py
│   ├── agent_config.py           ✅
│   └── snapshot.py               ✅
├── eval/
│   ├── __init__.py
│   ├── test_suite.py             ✅
│   ├── metrics.py                ✅
│   ├── bootstrap.py              ✅
│   ├── variance.py               ✅
│   └── evaluator.py              ✅
├── llm/
│   ├── __init__.py
│   ├── adapter.py                ✅
│   ├── openai_compat.py          ✅
│   ├── ollama.py                 ✅
│   └── escalation.py             ✅
├── mutations/
│   ├── __init__.py
│   ├── base.py                   ✅
│   ├── prompt.py                 ✅
│   ├── tool_desc.py              # Phase 2
│   ├── tool_impl.py              # Phase 2
│   ├── config_value.py           # Phase 2
│   ├── architecture.py           # Phase 4
│   ├── ladder.py                 ✅
│   └── proposer.py               ✅
├── runner/
│   ├── __init__.py               # Phase 1
│   ├── agent_runner.py           # Phase 1
│   └── tool_sandbox.py           # Phase 2
├── mock/
│   ├── __init__.py               # Phase 4
│   ├── engine.py                 # Phase 4
│   └── target.py                 # Phase 4
├── attribution/
│   ├── __init__.py               # Phase 3
│   ├── tracer.py                 # Phase 3
│   ├── ablation.py               # Phase 3
│   └── matrix.py                 # Phase 3
└── history/
    ├── __init__.py
    ├── store.py                  ✅
    └── analysis.py               # Phase 3
```

---

## Appendix: `_get_tests_from_context` Fix

There's a known stub in `mutations/prompt.py` line 87-89:

```python
def _get_tests_from_context(context: MutationContext) -> list[Any]:
    """Extract test cases from eval report metadata if available."""
    return []
```

This needs to be resolved in Phase 1. Two options:
1. **Add `test_suite` to `MutationContext`** — cleanest, but increases coupling
2. **Store test cases in `EvalReport.metadata`** — evaluator already has them

**Recommendation**: Option 1. Add `test_suite: TestSuite | None = None` to `MutationContext`. The optimizer creates the context with the test suite it already holds. This is the most natural place for it.
