"""Tests for MutationProposer — proposal parsing, type validation."""
from __future__ import annotations

import json

import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal
from prompter.mutations.ladder import LadderState
from prompter.mutations.proposer import MutationProposer, _parse_proposal
from tests.conftest import MockLLM


class TestParseProposal:
    def test_valid_json(self) -> None:
        content = json.dumps({
            "mutation_type": "prompt.rewrite",
            "rationale": "Fix failures",
            "target_tests": ["t1"],
            "target_components": ["system_prompt"],
            "params": {},
        })
        proposal = _parse_proposal(content, ["prompt.rewrite"])
        assert proposal.mutation_type == "prompt.rewrite"
        assert proposal.rationale == "Fix failures"

    def test_json_in_markdown_fence(self) -> None:
        content = "```json\n" + json.dumps({
            "mutation_type": "prompt.rewrite",
            "rationale": "Fix",
            "target_tests": [],
            "target_components": [],
        }) + "\n```"
        proposal = _parse_proposal(content, ["prompt.rewrite"])
        assert proposal.mutation_type == "prompt.rewrite"

    def test_json_with_surrounding_text(self) -> None:
        content = "Here is my proposal: " + json.dumps({
            "mutation_type": "prompt.rewrite",
            "rationale": "Fix",
        }) + " end"
        proposal = _parse_proposal(content, ["prompt.rewrite"])
        assert proposal.mutation_type == "prompt.rewrite"

    def test_invalid_type_falls_back(self) -> None:
        content = json.dumps({
            "mutation_type": "nonexistent.type",
            "rationale": "Fix",
        })
        proposal = _parse_proposal(content, ["prompt.rewrite"])
        assert proposal.mutation_type == "prompt.rewrite"  # Falls back to first allowed

    def test_unparseable_raises(self) -> None:
        with pytest.raises(ValueError, match="Could not parse"):
            _parse_proposal("not json at all", ["prompt.rewrite"])


class TestMutationProposer:
    async def test_propose_returns_valid_proposal(self) -> None:
        llm = MockLLM(responses=[json.dumps({
            "mutation_type": "prompt.rewrite",
            "rationale": "Better prompt needed",
            "target_tests": ["t1"],
            "target_components": ["system_prompt"],
            "params": {},
        })])

        proposer = MutationProposer(llm)
        config = AgentConfig(system_prompt="Basic prompt")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        ladder = LadderState()

        proposal = await proposer.propose(context, ladder)

        assert isinstance(proposal, MutationProposal)
        assert proposal.mutation_type == "prompt.rewrite"
