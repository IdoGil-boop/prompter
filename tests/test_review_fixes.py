"""Tests for code-reviewer and silent-failure-hunter HIGH issues.

Issue 1: EvalMode Literal missing "contains_match"
Issue 2: _get_tests_from_context stub returns []
Issue 3: httpx clients never closed — resource leak
Issue 4: Optimizer re-evaluates baseline at return
Issue 5: IndexError on empty allowed_types
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, get_args
import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.eval.metrics import METRIC_REGISTRY
from prompter.eval.test_suite import EvalMode, TestCase, TestSuite
from prompter.llm.adapter import LLMResponse, Message, TokenUsage
from prompter.mutations.base import MutationContext, MutationProposal
from prompter.mutations.prompt import SystemPromptMutation, _get_tests_from_context
from prompter.mutations.proposer import _parse_proposal
from tests.conftest import MockLLM


# --- Issue 1: EvalMode Literal missing "contains_match" ---

class TestEvalModeLiteral:
    def test_contains_match_in_eval_mode(self) -> None:
        """EvalMode Literal type should include all modes from METRIC_REGISTRY."""
        eval_mode_values = set(get_args(EvalMode))
        registry_keys = set(METRIC_REGISTRY.keys())
        assert "contains_match" in eval_mode_values, (
            f"'contains_match' missing from EvalMode. "
            f"EvalMode has {eval_mode_values}, registry has {registry_keys}"
        )

    def test_eval_mode_matches_metric_registry(self) -> None:
        """EvalMode Literal should match METRIC_REGISTRY keys exactly."""
        eval_mode_values = set(get_args(EvalMode))
        registry_keys = set(METRIC_REGISTRY.keys())
        assert eval_mode_values == registry_keys, (
            f"EvalMode {eval_mode_values} != METRIC_REGISTRY {registry_keys}"
        )


# --- Issue 2: _get_tests_from_context stub returns [] ---

class TestGetTestsFromContext:
    def test_returns_tests_when_test_suite_provided(self) -> None:
        """When MutationContext has a test_suite, _get_tests_from_context should return its tests."""
        config = AgentConfig(system_prompt="test")
        report = EvalReport(config_id="x", aggregate_score=0.5, results=[
            TestResult(test_id="t1", score=0.0, actual_output="wrong"),
        ])
        suite = TestSuite(tests=[
            TestCase(id="t1", input="hello", expected="world", eval_mode="exact_match"),
            TestCase(id="t2", input="foo", expected="bar", eval_mode="exact_match"),
        ])
        context = MutationContext(
            config=config, eval_report=report, history=[], test_suite=suite,
        )
        tests = _get_tests_from_context(context)
        assert len(tests) == 2
        assert tests[0].id == "t1"

    def test_returns_empty_when_no_test_suite(self) -> None:
        """When MutationContext has no test_suite, _get_tests_from_context should return []."""
        config = AgentConfig(system_prompt="test")
        report = EvalReport(config_id="x", aggregate_score=0.5, results=[])
        context = MutationContext(
            config=config, eval_report=report, history=[], test_suite=None,
        )
        tests = _get_tests_from_context(context)
        assert tests == []

    def test_mutation_context_has_test_suite_field(self) -> None:
        """MutationContext should accept an optional test_suite field."""
        config = AgentConfig(system_prompt="test")
        report = EvalReport(config_id="x", aggregate_score=0.5, results=[])
        # Should not raise
        ctx = MutationContext(
            config=config, eval_report=report, history=[], test_suite=None,
        )
        assert ctx.test_suite is None

    async def test_prompt_mutation_uses_test_suite(self) -> None:
        """SystemPromptMutation should use test_suite tests to build failure descriptions."""
        llm = MockLLM(responses=["Improved prompt"])
        mutation = SystemPromptMutation(llm)

        config = AgentConfig(system_prompt="You are basic.")
        suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])
        report = EvalReport(
            config_id="test", aggregate_score=0.0,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(
            config=config, eval_report=report, history=[], test_suite=suite,
        )
        proposal = MutationProposal(
            mutation_type="prompt.rewrite", rationale="fix",
            target_tests=["t1"], target_components=["system_prompt"], cost_tier=1,
        )
        result = await mutation.apply(context, proposal)
        # Verify the LLM received failure descriptions that include test input/expected
        call_messages = llm._call_log[0]
        user_msg = call_messages[-1].content
        assert "Say hello" in user_msg, "Test input should appear in the LLM prompt"
        assert "hello" in user_msg, "Expected output should appear in the LLM prompt"


# --- Issue 3: httpx clients — async context manager ---

class TestLLMAdapterContextManager:
    async def test_openai_compat_async_context_manager(self) -> None:
        """OpenAICompatAdapter should support async with for resource cleanup."""
        from prompter.llm.openai_compat import OpenAICompatAdapter

        adapter = OpenAICompatAdapter(base_url="http://localhost:1234", api_key="test")
        assert hasattr(adapter, "__aenter__"), "Missing __aenter__ method"
        assert hasattr(adapter, "__aexit__"), "Missing __aexit__ method"

        # Verify it works as a context manager
        async with adapter as a:
            assert a is adapter

    async def test_ollama_async_context_manager(self) -> None:
        """OllamaAdapter should support async with for resource cleanup."""
        from prompter.llm.ollama import OllamaAdapter

        adapter = OllamaAdapter(base_url="http://localhost:11434")
        assert hasattr(adapter, "__aenter__"), "Missing __aenter__ method"
        assert hasattr(adapter, "__aexit__"), "Missing __aexit__ method"

        async with adapter as a:
            assert a is adapter


# --- Issue 4: Optimizer re-evaluates baseline at return ---

class TestOptimizerBaselineReuse:
    async def test_baseline_not_reevaluated_at_return(self) -> None:
        """The optimizer should NOT re-evaluate baseline config at return time.

        It should reuse the initial baseline_report instead.
        """
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])

        # Perfect agent so it stops at iteration 0
        def perfect_agent(messages: list[Message]) -> str:
            return "hello"

        llm = MockLLM(responses=perfect_agent)

        from prompter.optimizer import Optimizer, OptimizerConfig

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=1,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
            )
            optimizer = Optimizer(
                config=config, test_suite=test_suite,
                llm=llm, opt_config=opt_config,
                history_path=Path(tmp) / "h.jsonl",
            )

            # Count how many times _evaluate is called
            original_evaluate = optimizer._evaluate
            eval_count = 0
            eval_configs: list[str] = []

            async def counting_evaluate(cfg: AgentConfig) -> EvalReport:
                nonlocal eval_count
                eval_count += 1
                eval_configs.append(cfg.config_hash())
                return await original_evaluate(cfg)

            optimizer._evaluate = counting_evaluate  # type: ignore[assignment]

            result = await optimizer.run()

        # With perfect agent: baseline eval (1) + final eval of best (1) = 2
        # BUG: without fix, there's an extra re-eval of original config = 3
        # The baseline_report in the return should be the stored one, not re-evaluated
        assert eval_count <= 2, (
            f"Expected at most 2 evaluations (baseline + final), got {eval_count}. "
            f"Configs evaluated: {eval_configs}"
        )


# --- Issue 5: IndexError on empty allowed_types ---

class TestEmptyAllowedTypes:
    def test_parse_proposal_empty_allowed_types_raises_valueerror(self) -> None:
        """_parse_proposal should raise ValueError (not IndexError) when allowed_types is empty."""
        content = json.dumps({
            "mutation_type": "prompt.rewrite",
            "rationale": "Fix",
        })
        with pytest.raises(ValueError, match="allowed_types"):
            _parse_proposal(content, [])
