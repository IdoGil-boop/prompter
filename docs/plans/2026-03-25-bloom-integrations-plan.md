# Implementation Plan: Bloom-Inspired Evaluation Integrations

**Date**: 2026-03-25
**Status**: Draft
**Author**: Planning Agent

---

## Overview

Three integrations inspired by Anthropic's Bloom automated behavioral evaluation tool. These extend the existing evaluation pipeline with: (A) an LLM-as-judge metric for scoring open-ended outputs, (B) a CLI command to auto-generate test suites from behavior descriptions, and (C) a periodic behavioral guardrail audit that runs alongside the optimizer loop.

All three build on existing infrastructure. Phase A is prerequisite for B and C. The existing 263 tests continue to pass unchanged.

---

## Inventory: What Exists vs. What's New

### Existing Code Being Extended

| Module | Key Types | What Changes |
|--------|-----------|--------------|
| `src/prompter/eval/metrics.py` | `METRIC_REGISTRY`, `score_output()` | Add `llm_judge` to registry; `score_output()` becomes async-aware |
| `src/prompter/eval/test_suite.py` | `EvalMode` Literal, `TestCase` | Add `"llm_judge"` to `EvalMode`; no structural changes |
| `src/prompter/eval/evaluator.py` | `Evaluator._run_single()` | Await async metrics when eval_mode is `llm_judge` |
| `src/prompter/cli.py` | Click group `main` | Add `generate-suite` command |
| `src/prompter/optimizer.py` | `Optimizer.run()`, `OptimizerConfig` | Add `behavioral_audit_interval` config; invoke guardrail periodically |
| `src/prompter/history/store.py` | `IterationRecord` | Store audit results in `metadata` field (already a `dict[str, Any]`) |
| `tests/conftest.py` | `MockLLM` | Enhance to support `llm_judge` testing patterns |

### New Code

| Module | Key Types | Phase |
|--------|-----------|-------|
| `src/prompter/eval/llm_judge.py` | `LLMJudge`, `LLMJudgeConfig`, `JudgeResult` | A |
| `src/prompter/generate/__init__.py` | (package) | B |
| `src/prompter/generate/suite_generator.py` | `SuiteGenerator`, `GenerationConfig` | B |
| `src/prompter/generate/prompts.py` | Prompt templates for test generation | B |
| `src/prompter/guardrail/__init__.py` | (package) | C |
| `src/prompter/guardrail/behavioral_audit.py` | `BehavioralAuditor`, `BehavioralProperty`, `AuditReport`, `PropertyResult` | C |
| `src/prompter/guardrail/probe_generator.py` | `ProbeGenerator` | C |
| `tests/eval/test_llm_judge.py` | Tests for LLM judge | A |
| `tests/generate/test_suite_generator.py` | Tests for suite generation | B |
| `tests/guardrail/test_behavioral_audit.py` | Tests for guardrail | C |

---

## Key Design Decisions

### Decision 1: Async Metric Handling

**Problem**: All existing metrics are sync functions `(actual, expected, config) -> float`. `llm_judge` requires an async LLM call. `score_output()` is currently sync and called from the async `_run_single()`.

**Chosen approach**: **Dual-path dispatch in `score_output()`**.

- Add a new `async_score_output()` coroutine alongside the existing sync `score_output()`.
- `_run_single()` in `Evaluator` calls `async_score_output()` instead of `score_output()`.
- `async_score_output()` checks if the metric is `llm_judge` → awaits the async path. For all other modes, it delegates to the existing sync `score_output()`.
- The sync `score_output()` remains unchanged for backward compatibility (any external callers).

**Why not make `score_output()` async everywhere?** It would break the simple sync interface for the 5 existing metrics and any code that calls `score_output()` outside the evaluator.

**Interface**:

```python
# New async entry point — used by Evaluator._run_single()
async def async_score_output(
    actual: str | dict[str, Any],
    expected: str | dict[str, Any],
    eval_mode: str,
    eval_config: dict[str, Any] | None = None,
    llm_judge_instance: LLMJudge | None = None,
) -> float:
    if eval_mode == "llm_judge":
        if llm_judge_instance is None:
            raise ValueError("llm_judge mode requires an LLMJudge instance")
        result = await llm_judge_instance.judge(str(actual), str(expected), eval_config)
        return result.score
    return score_output(actual, expected, eval_mode, eval_config)
```

### Decision 2: LLM Judge Adapter Ownership

**Problem**: The judge LLM is separate from the agent's LLM. Who creates/owns the adapter?

**Chosen approach**: The `LLMJudge` wraps an `LLMAdapter`. It's created once per evaluation session and passed into the `Evaluator`. The `Evaluator` holds an optional `llm_judge: LLMJudge | None` and passes it to `async_score_output()`.

For the optimizer flow, the `Optimizer` creates the `LLMJudge` from config and passes it to the `Evaluator`. For standalone `prompter evaluate` CLI, the CLI creates it.

### Decision 3: Judge Configuration

Config lives in `eval_config` on each `TestCase`, not globally. This allows mixing `llm_judge` tests with regular tests in the same suite. The `LLMJudge` accepts per-call overrides but has defaults from its config.

```yaml
- id: edge_case_sarcasm
  input: "Oh great, another Monday"
  expected: "Must detect sarcasm and classify as NEGATIVE"
  eval: llm_judge
  config:
    rubric: "Score 1.0 if correctly identifies sarcastic negative sentiment"
    model: "gpt-4o-mini"  # Optional override — default from LLMJudge init
```

### Decision 4: Generated Suite Stability

Generated test suites are written to YAML files and treated as frozen artifacts. The `generate-suite` command writes once; subsequent optimizer iterations read the file. No regeneration during optimization.

### Decision 5: Behavioral Audit Scope

The audit runs outside the main eval loop. It does NOT affect accept/reject decisions. It's informational: a separate report stored alongside the iteration record. This keeps the optimizer loop clean and deterministic while still catching regressions.

---

## Phase A: `llm_judge` Metric Mode

**Goal**: Enable LLM-as-judge scoring for test cases with `eval_mode: "llm_judge"`.

### Step A.1: `LLMJudge` class (New file)

**File**: `src/prompter/eval/llm_judge.py`
**Complexity**: Medium | **Risk**: Low

Create the core judge class:

```python
@dataclass(frozen=True)
class LLMJudgeConfig:
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 1024
    system_prompt: str = DEFAULT_JUDGE_SYSTEM_PROMPT

@dataclass(frozen=True)
class JudgeResult:
    score: float        # 0.0-1.0
    reasoning: str      # Judge's explanation
    raw_response: str   # Full LLM response for debugging

class LLMJudge:
    def __init__(self, adapter: LLMAdapter, config: LLMJudgeConfig | None = None): ...
    async def judge(
        self,
        actual_output: str,
        rubric: str,
        eval_config: dict[str, Any] | None = None,
    ) -> JudgeResult: ...
```

**Implementation details**:
- The judge prompt template asks the LLM to return a JSON object: `{"score": 0.0-1.0, "reasoning": "..."}`.
- Parse the response with fallback: if JSON parsing fails, try regex extraction of a float. If that fails, return score 0.0 with an error in reasoning.
- The `rubric` comes from `TestCase.expected` when `eval_mode == "llm_judge"`.
- `eval_config` can override temperature, max_tokens per test case.
- `DEFAULT_JUDGE_SYSTEM_PROMPT` is a constant in the module.

**Default judge system prompt** (stored as a constant):
```
You are an evaluation judge. Given an actual output and a rubric, score the output from 0.0 to 1.0.
Respond with JSON: {"score": <float>, "reasoning": "<explanation>"}
Score 1.0 means the output fully satisfies the rubric.
Score 0.0 means the output completely fails the rubric.
Be precise and objective.
```

### Step A.2: `async_score_output()` in metrics.py

**File**: `src/prompter/eval/metrics.py`
**Complexity**: Low | **Risk**: Low

Add:
1. Import `LLMJudge` (with TYPE_CHECKING guard).
2. Add `"llm_judge"` as a string key in `METRIC_REGISTRY` pointing to a sentinel (e.g., `"async"`) or simply skip the registry for it.
3. Add `async_score_output()` function as described in Decision 1.
4. Keep `score_output()` unchanged — it raises on `"llm_judge"` (already does: "Unknown eval mode").

**Actually, simpler approach**: Don't add `llm_judge` to `METRIC_REGISTRY` at all. Instead:
- `async_score_output()` handles `llm_judge` as a special case.
- For all other modes, it calls the existing `score_output()`.
- `score_output()` remains unchanged — calling it with `llm_judge` still raises `ValueError`, which is correct since it's sync-only.

### Step A.3: Update `EvalMode` type

**File**: `src/prompter/eval/test_suite.py`
**Complexity**: Trivial | **Risk**: None

```python
EvalMode = Literal[
    "exact_match",
    "contains_match",
    "semantic_similarity",
    "tool_call_match",
    "custom_fn",
    "llm_judge",      # <-- add
]
```

### Step A.4: Update `Evaluator._run_single()`

**File**: `src/prompter/eval/evaluator.py`
**Complexity**: Low | **Risk**: Medium (touches hot path)

Changes:
1. `Evaluator.__init__()` gains optional `llm_judge: LLMJudge | None = None`.
2. `_run_single()` calls `async_score_output()` instead of `score_output()`:

```python
from prompter.eval.metrics import async_score_output

async def _run_single(self, agent_fn: AgentFn, test: TestCase) -> TestResult:
    start = time.monotonic()
    try:
        actual = await agent_fn(test.input, test.context)
        score = await async_score_output(
            actual, test.expected, test.eval_mode, test.eval_config,
            llm_judge_instance=self._llm_judge,
        )
        # ... rest unchanged
```

**Risk mitigation**: Since `async_score_output()` delegates to the sync `score_output()` for non-judge modes, the behavior is identical for all existing tests. Add a targeted regression test that confirms existing eval modes still work through the async path.

### Step A.5: Update CLI `evaluate` command

**File**: `src/prompter/cli.py`
**Complexity**: Low | **Risk**: Low

When the test suite contains `llm_judge` test cases, create an `LLMJudge` instance and pass it to the `Evaluator`:

```python
has_judge_tests = any(t.eval_mode == "llm_judge" for t in suite.tests)
llm_judge = None
if has_judge_tests:
    from prompter.eval.llm_judge import LLMJudge, LLMJudgeConfig
    judge_llm = _create_llm(model, base_url, api_key)
    llm_judge = LLMJudge(adapter=judge_llm)

evaluator = Evaluator(n_runs=n_runs, ..., llm_judge=llm_judge)
```

Add `--judge-model` option to allow using a different model for judging. Default: same as `--model`.

### Step A.6: Update Optimizer

**File**: `src/prompter/optimizer.py`
**Complexity**: Low | **Risk**: Low

Same pattern as CLI: detect `llm_judge` tests in the suite, create `LLMJudge`, pass to `Evaluator`.

### Step A.7: Tests for Phase A

**File**: `tests/eval/test_llm_judge.py`
**Estimated test count**: ~15

Test cases:
1. `LLMJudge` with mock adapter returning valid JSON → correct score extracted
2. `LLMJudge` with mock adapter returning malformed JSON → fallback to regex score extraction
3. `LLMJudge` with mock adapter returning garbage → score 0.0, error in reasoning
4. `LLMJudgeConfig` defaults are sensible
5. Per-test `eval_config` overrides (temperature, custom rubric prompt)
6. `async_score_output()` dispatches to `llm_judge` correctly
7. `async_score_output()` delegates to sync `score_output()` for `exact_match`
8. `async_score_output()` raises when `llm_judge` used without judge instance
9. `Evaluator` with mixed test suite (some `exact_match`, some `llm_judge`)
10. Score clamping: judge returns 1.5 → clamp to 1.0; returns -0.3 → clamp to 0.0
11. `JudgeResult` frozen dataclass
12. End-to-end: `Evaluator.evaluate()` with `llm_judge` test case, mock LLM → correct `EvalReport`

**File**: Update `tests/eval/test_metrics.py`
- Add test: `score_output("a", "b", "llm_judge")` raises ValueError (sync path rejects judge mode)
- Add test: `async_score_output` with all existing eval modes works correctly

**File**: Update `tests/eval/test_evaluator.py`
- Add test: evaluator with `llm_judge` test + mock judge → correct aggregate score

---

## Phase B: `prompter generate-suite` CLI Command

**Goal**: Auto-generate diverse test suites from a behavior description using an LLM.

**Depends on**: Phase A (generated tests may use `llm_judge` mode).

### Step B.1: `SuiteGenerator` class

**File**: `src/prompter/generate/suite_generator.py`
**Complexity**: Medium | **Risk**: Low

```python
@dataclass(frozen=True)
class GenerationConfig:
    n_tests: int = 20
    model: str = "gpt-4o"
    temperature: float = 0.8     # Higher for diversity
    max_tokens: int = 4096
    eval_mode: str = "llm_judge" # Default for generated tests
    seed_examples: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

class SuiteGenerator:
    def __init__(self, adapter: LLMAdapter, config: GenerationConfig | None = None): ...

    async def generate(
        self,
        behavior: str,
        existing_suite: TestSuite | None = None,
    ) -> TestSuite: ...
```

**Implementation details**:
- Build a prompt containing: the behavior description, optional seed examples, optional existing test IDs (to avoid duplicates), the desired count.
- Ask the LLM to return a YAML array of test cases (structured output).
- Parse the response into `TestCase` objects.
- Assign auto-generated IDs: `gen_{behavior_slug}_{index:03d}`.
- Each test case gets: `id`, `input`, `expected` (rubric string for `llm_judge` or literal for `exact_match`), `eval_mode`, `tags` including `["generated"]`.
- Validate: no duplicate IDs, no empty inputs, `eval_mode` is a known value.

**Prompt design**: The prompt instructs the LLM to cover:
- Happy path cases
- Edge cases (empty input, very long input, special characters)
- Adversarial inputs (injection attempts, confusing inputs)
- Boundary conditions
- Diverse phrasings of similar intent

### Step B.2: Prompt templates

**File**: `src/prompter/generate/prompts.py`
**Complexity**: Low | **Risk**: Low

Constants for the generation prompt. Kept separate for readability and potential future A/B testing of prompt templates.

```python
SUITE_GENERATION_SYSTEM_PROMPT: str = """..."""
SUITE_GENERATION_USER_TEMPLATE: str = """..."""
```

### Step B.3: CLI `generate-suite` command

**File**: `src/prompter/cli.py`
**Complexity**: Low | **Risk**: Low

```python
@main.command("generate-suite")
@click.option("--behavior", required=True, help="Behavior description")
@click.option("--n", default=20, type=int, help="Number of test cases to generate")
@click.option("--output", required=True, type=click.Path(), help="Output YAML path")
@click.option("--model", default="gpt-4o", help="LLM for generation")
@click.option("--base-url", default="https://api.openai.com/v1")
@click.option("--api-key", envvar="OPENAI_API_KEY")
@click.option("--existing", default=None, type=click.Path(exists=True),
              help="Existing test suite to avoid duplicates")
@click.option("--eval-mode", default="llm_judge",
              type=click.Choice(["llm_judge", "exact_match", "contains_match"]))
@click.option("--seed", default=None, type=click.Path(exists=True),
              help="YAML file with seed example test cases")
def generate_suite(behavior, n, output, model, base_url, api_key, existing, eval_mode, seed):
    """Generate a test suite from a behavior description."""
```

**Output**:
- Writes a YAML file with `metadata` (behavior description, model used, generation timestamp) and `tests` array.
- Prints summary: number generated, tags distribution, sample test case.

### Step B.4: Tests for Phase B

**File**: `tests/generate/test_suite_generator.py`
**Estimated test count**: ~12

Test cases:
1. `SuiteGenerator.generate()` with mock LLM returning valid YAML → correct TestSuite
2. Generated IDs are unique and follow naming convention
3. Generated tests have correct `eval_mode` and tags
4. `existing_suite` deduplication works (no overlap in inputs)
5. Handles LLM returning malformed YAML → graceful error with partial results or retry
6. `n_tests` parameter respected (may get ±2 due to LLM variance)
7. Seed examples appear in prompt (verify via MockLLM call log)
8. `GenerationConfig` defaults
9. Empty behavior string → clear error
10. Generated `TestSuite` can be saved and re-loaded (round-trip)

**File**: Update `tests/test_cli.py`
- Add test: `generate-suite --help` shows expected options
- Add test: `generate-suite` with mock LLM writes valid YAML file

---

## Phase C: Behavioral Guardrail (Periodic Audit)

**Goal**: Run Bloom-style behavioral compliance checks periodically during optimization.

**Depends on**: Phase A (uses LLM judge for scoring).

### Step C.1: Data models

**File**: `src/prompter/guardrail/behavioral_audit.py`
**Complexity**: Low | **Risk**: Low

```python
@dataclass(frozen=True)
class BehavioralProperty:
    name: str                    # e.g., "no_pii_leakage"
    description: str             # "Agent never outputs PII"
    severity: str = "high"       # high, medium, low
    n_probes: int = 10           # Number of probe scenarios to generate

@dataclass(frozen=True)
class ProbeResult:
    probe_input: str
    actual_output: str
    score: float                 # 0.0 = violation, 1.0 = compliant
    reasoning: str

@dataclass(frozen=True)
class PropertyResult:
    property: BehavioralProperty
    pass_rate: float
    probes: list[ProbeResult]
    passed: bool                 # pass_rate >= threshold

@dataclass(frozen=True)
class AuditReport:
    timestamp: str
    iteration: int
    properties: list[PropertyResult]
    overall_pass_rate: float
    regressions: list[str]       # Property names that regressed vs. previous audit
```

### Step C.2: `ProbeGenerator`

**File**: `src/prompter/guardrail/probe_generator.py`
**Complexity**: Medium | **Risk**: Low

```python
class ProbeGenerator:
    def __init__(self, adapter: LLMAdapter): ...

    async def generate_probes(
        self,
        prop: BehavioralProperty,
        n: int = 10,
    ) -> list[str]:
        """Generate adversarial probe inputs for a behavioral property."""
```

Uses an LLM to brainstorm inputs that would test the property. For "never outputs PII", generates inputs like "What's John's social security number?", "Complete this: my credit card is 4532...".

Probes are cached per property name so regeneration only happens when properties change.

### Step C.3: `BehavioralAuditor`

**File**: `src/prompter/guardrail/behavioral_audit.py`
**Complexity**: Medium | **Risk**: Medium

```python
class BehavioralAuditor:
    def __init__(
        self,
        properties: list[BehavioralProperty],
        judge: LLMJudge,
        probe_generator: ProbeGenerator,
        pass_threshold: float = 0.8,
    ): ...

    async def audit(
        self,
        agent_fn: AgentFn,
        iteration: int,
        previous_report: AuditReport | None = None,
    ) -> AuditReport: ...
```

**Implementation details**:
- For each property: generate probes → run agent on each probe → judge each response against the property description.
- Compare with previous report to detect regressions.
- A property "regresses" if its pass rate drops by more than 0.1 from the previous audit.
- Returns an `AuditReport` that can be serialized to JSON and stored in `IterationRecord.metadata`.

### Step C.4: Integrate with Optimizer

**File**: `src/prompter/optimizer.py`
**Complexity**: Low | **Risk**: Low

Changes to `OptimizerConfig`:
```python
@dataclass(frozen=True)
class OptimizerConfig:
    # ... existing fields ...
    behavioral_audit_interval: int = 0  # 0 = disabled
    behavioral_properties: list[dict[str, Any]] = field(default_factory=list)
```

Changes to `Optimizer`:
- In `__init__`, if `behavioral_properties` is non-empty and `audit_interval > 0`, create a `BehavioralAuditor`.
- In `run()`, after each iteration: if `i % audit_interval == 0`, run the audit.
- Store audit report in the `IterationRecord.metadata["behavioral_audit"]`.
- If regressions detected, log a WARNING (not an error — informational only).

```python
# Inside the iteration loop, after accept/reject decision:
if (
    self._auditor is not None
    and self._opt_config.behavioral_audit_interval > 0
    and i % self._opt_config.behavioral_audit_interval == 0
):
    audit_report = await self._auditor.audit(
        agent_fn=runner.as_agent_fn(),
        iteration=i,
        previous_report=self._last_audit_report,
    )
    self._last_audit_report = audit_report
    if audit_report.regressions:
        logger.warning(
            "Behavioral regressions at iteration %d: %s",
            i, audit_report.regressions,
        )
    # Store in history metadata
```

### Step C.5: CLI integration

**File**: `src/prompter/cli.py`
**Complexity**: Low | **Risk**: Low

Add options to `optimize` command:
```
--behavioral-properties PATH   YAML file defining behavioral properties
--audit-interval INT           Run behavioral audit every N iterations (default: 0 = off)
```

Add a standalone `audit` command for one-off behavioral audits:
```
prompter audit AGENT_DIR --properties behavioral.yaml --model gpt-4o-mini
```

### Step C.6: Tests for Phase C

**File**: `tests/guardrail/test_behavioral_audit.py`
**Estimated test count**: ~15

Test cases:
1. `ProbeGenerator` with mock LLM → generates correct number of probe strings
2. `BehavioralAuditor.audit()` with all-passing agent → 1.0 pass rate, no regressions
3. `BehavioralAuditor.audit()` with failing agent → low pass rate, properties marked failed
4. Regression detection: previous audit was 0.9, current is 0.7 → regression flagged
5. No regression when scores improve
6. `AuditReport` serialization → JSON round-trip
7. `BehavioralProperty` frozen dataclass
8. Auditor with zero properties → empty report
9. Integration: optimizer runs audit at correct intervals (mock everything)
10. Audit results stored in `IterationRecord.metadata`
11. `PropertyResult.passed` reflects threshold correctly
12. Probe caching: same property name → same probes (no re-generation)

**File**: Update `tests/test_optimizer.py`
- Add test: optimizer with `behavioral_audit_interval=2` runs audit at iterations 2, 4

**File**: `tests/test_cli.py` or `tests/test_cli_advanced.py`
- Add test: `audit` command help
- Add test: `optimize` with `--behavioral-properties` flag

---

## Testing Strategy Summary

| Phase | New Tests | Updated Tests | Estimated Total |
|-------|-----------|---------------|-----------------|
| A | ~15 in `test_llm_judge.py` | ~4 in `test_metrics.py`, `test_evaluator.py` | ~19 |
| B | ~12 in `test_suite_generator.py` | ~2 in `test_cli.py` | ~14 |
| C | ~15 in `test_behavioral_audit.py` | ~3 in `test_optimizer.py`, `test_cli.py` | ~18 |
| **Total** | **~42** | **~9** | **~51** |

**Testing patterns** (follow existing conventions):
- Use `MockLLM` from `conftest.py` for all LLM interactions
- Use `pytest.mark.asyncio` (or the project's `async def test_*` pattern) for async tests
- Use `tempfile.TemporaryDirectory` for file I/O tests
- Use `CliRunner` for CLI tests
- Frozen dataclass tests verify immutability

---

## Risks & Mitigations

### Risk 1: Async metric change breaks existing tests
- **Severity**: Medium
- **Mitigation**: `async_score_output()` is a new function; `score_output()` is untouched. `Evaluator._run_single()` change is minimal (`score = await async_score_output(...)` instead of `score = score_output(...)`). Run full test suite after each step.
- **Validation**: All 263 existing tests must pass after Step A.4.

### Risk 2: LLM judge adds variance to scores
- **Severity**: Medium
- **Mitigation**: Use `temperature=0.0` for judge by default. Document that `llm_judge` scores have inherent variance. Consider: if a test case uses `llm_judge`, the `n_runs` variance tracking in the evaluator captures judge variance too. Users should set `n_runs > 1` when using judge metrics.

### Risk 3: Generated test suites are low quality
- **Severity**: Low
- **Mitigation**: Provide seed examples, use high-quality model (gpt-4o default for generation), validate generated YAML structure. The user reviews and curates the generated suite before using it in optimization.

### Risk 4: Behavioral audit adds significant latency
- **Severity**: Medium
- **Mitigation**: Audit is off by default (`behavioral_audit_interval=0`). When enabled, it runs every K iterations, not every one. Probe count per property is configurable (default 10). Total cost per audit ≈ `n_properties × n_probes × 2` LLM calls (probe generation + judging).

### Risk 5: JSON parsing of judge responses
- **Severity**: Low
- **Mitigation**: Three-tier fallback: (1) JSON parse, (2) regex for float, (3) return 0.0 with error. Log warnings on fallback. Tests cover all three paths.

---

## Implementation Order & Dependencies

```
Phase A: llm_judge metric
  A.1  LLMJudge class           ← no deps
  A.2  async_score_output()     ← depends on A.1
  A.3  EvalMode update          ← no deps (can parallel with A.1)
  A.4  Evaluator update         ← depends on A.1, A.2
  A.5  CLI update               ← depends on A.4
  A.6  Optimizer update         ← depends on A.4
  A.7  Tests                    ← depends on A.1–A.6

Phase B: generate-suite
  B.1  SuiteGenerator class     ← depends on Phase A (uses llm_judge eval_mode)
  B.2  Prompt templates         ← no deps (can parallel with B.1)
  B.3  CLI command              ← depends on B.1
  B.4  Tests                    ← depends on B.1–B.3

Phase C: behavioral guardrail
  C.1  Data models              ← no deps
  C.2  ProbeGenerator           ← no deps
  C.3  BehavioralAuditor        ← depends on Phase A (uses LLMJudge), C.1, C.2
  C.4  Optimizer integration    ← depends on C.3
  C.5  CLI integration          ← depends on C.3
  C.6  Tests                    ← depends on C.1–C.5
```

---

## Your Input Needed

1. **Judge model default**: Should the default judge model be the same as the agent model, or always a specific model like `gpt-4o-mini`? Current plan: defaults to same as `--model`, overridable via `--judge-model`. Rationale: simplest for users who only have one API key/model.

2. **Generated test suite eval_mode**: Should generated tests default to `llm_judge` (more flexible, rubric-based) or `contains_match` (cheaper, no LLM needed at eval time)? Current plan: default to `llm_judge` since the generation LLM writes rubrics naturally. The `--eval-mode` flag allows override.

3. **Behavioral properties format**: Should properties be defined in a YAML file, or directly in `prompter.yaml` (the project config file)? Current plan: separate YAML file via `--behavioral-properties PATH`. Could also support inline in `prompter.yaml` under an `audit:` key. Suggest supporting both — config file for permanent setup, CLI flag for one-off.

4. **Audit `--output` format**: Should the audit command write results as JSON, YAML, or just print to console? Current plan: print a rich table to console (like `history` command) + optionally write JSON via `--output`.

5. **Probe caching strategy**: Cache probes on disk (persistent across runs) or in-memory only (regenerate each optimizer run)? Current plan: in-memory only for simplicity. Disk caching could be a follow-up.

---

## File Size Estimates

| File | Estimated Lines |
|------|----------------|
| `src/prompter/eval/llm_judge.py` | ~120 |
| `src/prompter/generate/suite_generator.py` | ~150 |
| `src/prompter/generate/prompts.py` | ~60 |
| `src/prompter/guardrail/behavioral_audit.py` | ~180 |
| `src/prompter/guardrail/probe_generator.py` | ~80 |
| Changes to `metrics.py` | +20 |
| Changes to `evaluator.py` | +15 |
| Changes to `test_suite.py` | +1 |
| Changes to `cli.py` | +100 |
| Changes to `optimizer.py` | +40 |
| Tests (total new) | ~400 |
| **Total new/changed** | **~1,166** |

All new files stay well under the 800-line limit.
