"""Tests for escalation integration in the optimizer loop."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from prompter.config.agent_config import AgentConfig
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.optimizer import Optimizer, OptimizerConfig
from tests.conftest import MockLLM

if TYPE_CHECKING:
    from prompter.llm.adapter import Message


class MockLLMTier(MockLLM):
    """MockLLM with configurable tier and model_id."""

    def __init__(
        self,
        responses: list[str] | object,
        tier_name: str = "local",
        model_name: str = "mock",
    ) -> None:
        super().__init__(responses)
        self._tier_name = tier_name
        self._model_name = model_name

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def tier(self) -> str:
        return self._tier_name


def _make_escalation_llm() -> MockLLM:
    """LLM that responds based on system prompt content for escalation tests."""

    def respond(messages: list[Message]) -> str:
        system = messages[0].content if messages and messages[0].role == "system" else ""
        user = messages[-1].content if messages else ""

        # Mutation proposer call
        if "optimization strategist" in system.lower():
            return json.dumps({
                "mutation_type": "prompt.rewrite",
                "rationale": "Improve prompt",
                "target_tests": [],
                "target_components": ["system_prompt"],
                "params": {},
            })

        # Mutation apply call
        if "prompt optimization expert" in system.lower():
            return "IMPROVED: Reply exactly with the expected output."

        # Agent call
        if "IMPROVED" in system:
            if "hello" in user.lower():
                return "hello"
            return user.lower().strip()

        return "I don't know"

    return MockLLM(responses=respond)


class TestOptimizerEscalation:
    """Tests for escalation tier integration in optimizer."""

    async def test_optimizer_accepts_escalation_tiers(self) -> None:
        """Optimizer should accept escalation_tiers parameter."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(
            tests=[
                TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            ]
        )
        main_llm = _make_escalation_llm()
        local_tier = MockLLMTier(responses=_make_escalation_llm()._responses, tier_name="local")
        cheap_tier = MockLLMTier(responses=_make_escalation_llm()._responses, tier_name="cheap")

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=2,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=main_llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
                escalation_tiers={"local": local_tier, "cheap": cheap_tier},
            )

            result = await optimizer.run()
            assert result is not None

    async def test_escalation_rejects_regressing_mutation(self) -> None:
        """When escalation detects regression at a tier, mutation should be rejected."""
        config = AgentConfig(system_prompt="Good prompt.")
        test_suite = TestSuite(
            tests=[
                TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            ]
        )


        def respond_main(messages: list[Message]) -> str:
            system = messages[0].content if messages and messages[0].role == "system" else ""
            messages[-1].content if messages else ""

            if "optimization strategist" in system.lower():
                return json.dumps({
                    "mutation_type": "prompt.rewrite",
                    "rationale": "Improve prompt",
                    "target_tests": [],
                    "target_components": ["system_prompt"],
                    "params": {},
                })

            if "prompt optimization expert" in system.lower():
                return "WORSE: This prompt is bad."

            # Good baseline
            if "Good prompt" in system:
                return "hello"
            # After mutation, regression
            return "wrong answer"

        def respond_local(messages: list[Message]) -> str:
            """Local tier also sees regression."""
            system = messages[0].content if messages and messages[0].role == "system" else ""
            if "WORSE" in system:
                return "wrong answer"
            return "hello"

        main_llm = MockLLM(responses=respond_main)
        local_tier = MockLLMTier(
            responses=respond_local, tier_name="local", model_name="local-model"
        )

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=1,
                target_score=1.0,
                n_eval_runs=1,
                compute_ci=False,
                improvement_threshold=0.01,
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=main_llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
                escalation_tiers={"local": local_tier},
            )

            result = await optimizer.run()
            # The optimizer should not have improved since escalation rejects regression
            # Best config should still be the original
            assert result.best_config.system_prompt == "Good prompt."

    async def test_optimizer_without_escalation_still_works(self) -> None:
        """Without escalation_tiers, optimizer should work as before."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(
            tests=[
                TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            ]
        )
        llm = _make_escalation_llm()

        with tempfile.TemporaryDirectory() as tmp:
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
                history_path=Path(tmp) / "history.jsonl",
            )

            result = await optimizer.run()
            assert result is not None
