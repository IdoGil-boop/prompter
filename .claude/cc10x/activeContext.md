# Active Context
<!-- CC10X: Do not rename headings. Used as Edit anchors. -->

## Current Focus
Phase 5+6 COMPLETE — 263/263 tests, mypy clean, ruff clean. All phases implemented.

## Recent Changes
[BUILD-START: wf:37]
- [2026-03-25] Phase 5+6 complete: escalation integration, variance hardening, config file, rich CLI, examples, CI, README — 263/263 tests
- [2026-03-25] Phase 4 complete: MockEngine, MockTarget, MockTargetOptimizer, 3 architecture mutations — 235/235 tests
- [2026-03-25] Review: APPROVE (90%), Hunt: CLEAN. No REM-FIX needed.

## Next Steps
1. All phases complete. Project ready for open-source release.
2. Consider: publish to PyPI, improve documentation site, add more examples.

## Decisions
- Architecture: autoresearch-style loop — iteratively mutate agent config, evaluate against user test suite, keep/revert
- Novel mechanism: mock-first, build-second — test hypotheses cheaply before implementing
- Two optimization loops: Loop 1 (what to build, mock-guided), Loop 2 (build it well, optimize toward mock artifact)
- Evaluation: user-provided labels as ground truth, bootstrap CI for statistical confidence
- Variance penalty: effective_score = mean_score - λ * variance
- Pseudo-backpropagation via component attribution matrix (ablation sweeps)
- Model escalation: local → cheap → SOTA for cost control
- Failure-directed search with typed mutation operators and escalation ladder

## Learnings
- ToolSandbox import restriction: pre-import allowed modules, then use _in_allowed_import flag to allow transitive deps while blocking user-level forbidden imports
- AgentRunner tool loop: append assistant msg with tool_calls, then tool results, then re-call LLM — standard agentic loop
- DSPy optimizes prompt text; this project optimizes the full agent stack (tools, RAG, context, memory)
- Mock artifacts become target labels for implementation optimization (embedding similarity, no LLM needed)
- Karpathy's autoresearch uses 3 files (prepare.py, train.py, program.md); we mirror with agent/, tests.yaml, program.md
- Mutation registry requires explicit import of mutation modules (e.g., `import prompter.mutations.prompt`) to populate via decorators
- pytest-asyncio mode=auto with asyncio_mode="auto" in pyproject.toml enables async test methods without explicit markers
- Phase 1 code follows frozen dataclass + Protocol + structured logging consistently
- custom_fn importlib.import_module is intentional user extensibility, not a security hole
- from __future__ import annotations makes TYPE_CHECKING imports safe for annotation-only usage
- Empty-guard pattern (raise ValueError before indexing) prevents silent failures from empty collections
- Optimizer loop uses intentional log-and-continue for proposer/mutation failures — correct for optimization loops
- Max-tool-rounds synthesis: call LLM with tools=None after loop exhaustion for graceful degradation
- Empty-implementation guard in AddToolMutation prevents silently creating stub tools that always fail
- context_label in _parse_json aids debugging which mutation produced invalid LLM output
- Attribution matrix uses _ablation sentinel key to distinguish ablation from trace data
- Ablation neutralizes system_prompt with generic string (can't remove it entirely)
- HistoryAnalyzer filters baseline records (mutation_type=None) before stagnation/effectiveness
- Frozen dataclasses for attribution results, mutable classes for accumulators (AttributionMatrix)
- AblationSweep is all-or-nothing per sweep; optimizer catches failures at top level
- Architecture mutations use _ArchitectureMutationBase shared base with _target_field/_component_name for DRY
- MockEngine.test_hypothesis uses direct mock agent_fn (not injected config) for hypothesis eval — simpler and more reliable
- MockTargetOptimizer uses LLM to improve implementations toward target outputs — cheap Loop 2 without full agent evaluation

## References
- [cc10x-internal] memory_task_id: 42 wf:37
- Plan: `docs/plans/2026-03-24-prompter-implementation-plan.md`
- Design: N/A
- Research: N/A
- Inspiration: https://github.com/karpathy/autoresearch

## Blockers
- None

## Last Updated
2026-03-25
