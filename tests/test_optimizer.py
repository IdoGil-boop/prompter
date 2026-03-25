"""Integration test for Optimizer — full loop with MockLLM."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from prompter.config.agent_config import AgentConfig
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.optimizer import OptimizationResult, Optimizer, OptimizerConfig
from tests.conftest import MockLLM

if TYPE_CHECKING:
    from prompter.llm.adapter import Message


def _make_smart_llm() -> MockLLM:
    """MockLLM that:
    - As agent: returns the input lowercased (bad baseline), but after prompt mutation,
      returns exact expected output when system prompt contains 'IMPROVED'.
    - As proposer: returns a valid mutation proposal JSON.
    - As mutator: returns an improved system prompt containing 'IMPROVED'.
    """
    def respond(messages: list[Message]) -> str:
        system = messages[0].content if messages and messages[0].role == "system" else ""
        user = messages[-1].content if messages else ""

        # Mutation proposer call: system contains "optimization strategist"
        if "optimization strategist" in system.lower():
            return json.dumps({
                "mutation_type": "prompt.rewrite",
                "rationale": "Improve the system prompt to handle exact outputs",
                "target_tests": [],
                "target_components": ["system_prompt"],
                "params": {},
            })

        # Mutation apply call: system contains "prompt optimization expert"
        if "prompt optimization expert" in system.lower():
            return "IMPROVED: You must reply with the exact expected output."

        # Agent call: check if prompt was improved
        if "IMPROVED" in system:
            # After improvement, return exact expected outputs
            if "hello" in user.lower():
                return "hello"
            if "goodbye" in user.lower():
                return "goodbye"
            if "yes" in user.lower():
                return "yes"
            return user.lower().strip()

        # Baseline agent: bad responses
        return "I don't know"

    return MockLLM(responses=respond)


class TestOptimizer:
    """Integration tests for the optimization loop."""

    async def test_optimizer_improves_score(self) -> None:
        """The optimizer should improve score from bad baseline to good via prompt mutation."""
        config = AgentConfig(system_prompt="You are a basic assistant.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="Say goodbye", expected="goodbye", eval_mode="exact_match"),
            TestCase(id="t3", input="Say yes", expected="yes", eval_mode="exact_match"),
        ])
        llm = _make_smart_llm()

        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"
            opt_config = OptimizerConfig(
                max_iterations=5,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
                improvement_threshold=0.01,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=history_path,
            )

            result = await optimizer.run()

        assert isinstance(result, OptimizationResult)
        assert result.final_report.aggregate_score > 0.0
        # After mutation, the improved prompt should yield better results
        assert result.final_report.aggregate_score > result.baseline_report.aggregate_score or \
               result.final_report.aggregate_score >= opt_config.target_score

    async def test_optimizer_stops_at_target_score(self) -> None:
        """If baseline already meets target, optimizer should return immediately."""
        # LLM that always returns exact match
        def perfect_agent(messages: list[Message]) -> str:
            user = messages[-1].content if messages else ""
            if "hello" in user.lower():
                return "hello"
            if "goodbye" in user.lower():
                return "goodbye"
            return "yes"

        config = AgentConfig(system_prompt="Perfect prompt.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="Say goodbye", expected="goodbye", eval_mode="exact_match"),
            TestCase(id="t3", input="Say yes", expected="yes", eval_mode="exact_match"),
        ])
        llm = MockLLM(responses=perfect_agent)

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=10,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
            )

            result = await optimizer.run()

        assert result.final_report.aggregate_score >= 1.0
        assert result.iterations_run == 0  # Should not iterate if already at target

    async def test_optimizer_records_history(self) -> None:
        """Optimizer should write iteration records to history store."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])
        llm = _make_smart_llm()

        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"
            opt_config = OptimizerConfig(
                max_iterations=2,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=history_path,
            )

            await optimizer.run()

            # History file should exist and have records
            assert history_path.exists()
            lines = [line for line in history_path.read_text().strip().split("\n") if line]
            assert len(lines) >= 1  # At least baseline record

    async def test_optimizer_saves_snapshots(self) -> None:
        """When snapshots_dir is set, optimizer should save config snapshots."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])
        llm = _make_smart_llm()

        with tempfile.TemporaryDirectory() as tmp:
            snapshots_dir = Path(tmp) / "snapshots"
            opt_config = OptimizerConfig(
                max_iterations=2,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
                snapshots_dir=snapshots_dir,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
            )

            await optimizer.run()

            assert snapshots_dir.exists()
            # Should have at least one snapshot directory
            snapshot_dirs = list(snapshots_dir.iterdir())
            assert len(snapshot_dirs) >= 1

    async def test_optimization_result_has_best_config(self) -> None:
        """OptimizationResult should contain the best config found."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])
        llm = _make_smart_llm()

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=3,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
            )

            result = await optimizer.run()

        assert isinstance(result.best_config, AgentConfig)
        assert result.best_config.system_prompt  # Should have a prompt
