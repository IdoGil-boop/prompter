# Project Patterns
<!-- CC10X MEMORY CONTRACT: Do not rename headings. Used as Edit anchors. -->

## User Standards
- Type hints on all public functions
- Structured logging (never print())
- Small functions (<50 lines), small files (<800 lines)
- No hardcoded values — use config/constants
- Async by default (I/O-bound LLM calls)
- Immutable data models (frozen dataclasses)

## Architecture Patterns
- AgentConfig is frozen/immutable — mutations produce new instances
- Everything logged to JSONL history — reproducibility non-negotiable
- LLMAdapter Protocol — user plugs in any LLM, no vendor lock-in
- Model escalation tiers: local → cheap → SOTA (fail fast, save money)
- Typed mutation operators with escalation ladder (cheap mutations before expensive)

## Code Conventions
- src layout: src/prompter/
- Config loading: YAML for user-facing, dataclasses for internal
- Protocol classes for adapters (not ABC)

## File Structure
- Source: src/prompter/<module>/<file>.py
- Tests: tests/unit/, tests/integration/, tests/fixtures/
- Examples: examples/<name>/

## Testing Patterns
- pytest + pytest-asyncio
- 80%+ coverage for new code
- Fixtures in tests/fixtures/sample_agent/

## Common Gotchas
- ToolSandbox import restriction: can't just check sys.modules (os is always cached); use _in_allowed_import re-entrancy flag to allow transitive deps from allowed modules while blocking direct imports of forbidden modules
- ESCALATION_TIERS uses TypedDict (TierInfo) to avoid mypy `object` type on dict values with mixed types
- Mutation base class __init__ takes no args; subclasses take llm — use `type: ignore[call-arg]` when instantiating from registry
- ruff TCH rules require TYPE_CHECKING blocks for imports used only in annotations (with `from __future__ import annotations`)
- sentence-transformers is optional — semantic_similarity falls back to token overlap
- LLM outputs are stochastic — always run N times for confidence
- Mock-vs-actual gap: real RAG may not match mock quality
- Mutation registry uses decorators at import time — must explicitly import mutation modules (e.g., `import prompter.mutations.prompt`) before accessing registry
- pytest tempfile.TemporaryDirectory: assertions must be INSIDE the `with` block, not after it
- TestCase/TestSuite classes trigger PytestCollectionWarning — benign, caused by __init__ on dataclasses named Test*
- [Deferred]: JSONL append not corruption-resilient — partial writes on crash leave malformed lines
- [Deferred]: Empty test suite produces 0.0 score without warning — optimizer silently wastes iterations
- [Deferred]: Empty LLM output (content="") returns score=0 with no logging — makes debugging difficult
- [Deferred]: Optimizer lacks consecutive-failure counter — if all iterations fail, no summary warning
- [Deferred]: metrics.py:152 silent pass in _parse_tool_call — acceptable but could use debug logging
- [Deferred]: ToolSandbox empty stdout returns "" with no warning — LLM gets empty tool result
- [Deferred]: _get_tool_name duplicated across tool_desc.py, tool_impl.py, tool_manage.py with inconsistent fallback
- [Deferred]: _parse_json duplicated in config_value.py and tool_manage.py — minor DRY violation
- [Deferred]: ToolSandbox import restriction not thread-safe (single-threaded subprocess makes it safe)
- [Deferred]: AblationSweep individual component failures abort entire sweep — partial results could be preserved
- [Deferred]: HistoryAnalyzer instantiated inside loop every iteration — could lift to __init__
- [Deferred]: AttributionMatrix never resets between optimizer runs — fine for single-run lifecycle

## API Patterns
- N/A (library, not service)

## Error Handling
- Specific exceptions with context
- AgentFn errors caught and returned as score=0.0 TestResults

## Dependencies
- pyyaml: config/test suite parsing
- httpx: async HTTP for LLM APIs
- click: CLI
- rich: terminal output
- numpy: bootstrap, attribution matrix
- sentence-transformers (optional): semantic similarity

## Project SKILL_HINTS
