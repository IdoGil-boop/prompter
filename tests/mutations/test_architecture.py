"""Tests for architecture mutations — RAG, context, memory with mock gating."""
from __future__ import annotations

import json

import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.mutations.architecture import (
    ContextArchitectureMutation,
    MemoryArchitectureMutation,
    RAGArchitectureMutation,
)
from prompter.mutations.base import (
    Mutation,
    MutationContext,
    MutationProposal,
    MutationResult,
)
from tests.conftest import MockLLM

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_config() -> AgentConfig:
    return AgentConfig(system_prompt="You are a helpful assistant.")


@pytest.fixture
def small_suite() -> TestSuite:
    return TestSuite(tests=[
        TestCase(id="t1", input="What is 2+2?", expected="4", eval_mode="exact_match"),
        TestCase(id="t2", input="What is 3+3?", expected="6", eval_mode="exact_match"),
    ])


@pytest.fixture
def eval_report() -> EvalReport:
    return EvalReport(
        config_id="test",
        aggregate_score=0.3,
        results=[
            TestResult(test_id="t1", score=0.0, actual_output="wrong"),
            TestResult(test_id="t2", score=0.6, actual_output="almost"),
        ],
    )


@pytest.fixture
def context(
    base_config: AgentConfig, eval_report: EvalReport, small_suite: TestSuite,
) -> MutationContext:
    return MutationContext(
        config=base_config,
        eval_report=eval_report,
        history=[],
        test_suite=small_suite,
    )


def _make_proposal(mutation_type: str) -> MutationProposal:
    return MutationProposal(
        mutation_type=mutation_type,
        rationale="Test failures suggest need for architectural change",
        target_tests=["t1", "t2"],
        target_components=["system_prompt"],
        cost_tier=6,
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_rag_mutation_registered(self) -> None:
        registry = Mutation.registry()
        assert "architecture.rag" in registry
        assert registry["architecture.rag"] is RAGArchitectureMutation

    def test_context_mutation_registered(self) -> None:
        registry = Mutation.registry()
        assert "architecture.context" in registry
        assert registry["architecture.context"] is ContextArchitectureMutation

    def test_memory_mutation_registered(self) -> None:
        registry = Mutation.registry()
        assert "architecture.memory" in registry
        assert registry["architecture.memory"] is MemoryArchitectureMutation


# ---------------------------------------------------------------------------
# Cost tiers
# ---------------------------------------------------------------------------

class TestCostTiers:
    def test_rag_cost_tier(self) -> None:
        assert RAGArchitectureMutation.cost_tier == 6

    def test_context_cost_tier(self) -> None:
        assert ContextArchitectureMutation.cost_tier == 6

    def test_memory_cost_tier(self) -> None:
        assert MemoryArchitectureMutation.cost_tier == 6


# ---------------------------------------------------------------------------
# RAG Architecture Mutation
# ---------------------------------------------------------------------------

class TestRAGArchitectureMutation:
    async def test_apply_returns_mutation_result(
        self, context: MutationContext,
    ) -> None:
        """RAG mutation should return a MutationResult with rag_config set."""
        # LLM responds with mock capability description then optimized impl
        responses = [
            # Mock engine hypothesis test - mock capability output
            json.dumps({
                "name": "knowledge_base",
                "description": "Domain knowledge retrieval",
                "mock_output": "relevant context for the query",
                "capability_type": "rag",
            }),
            # Optimization response
            "def rag_retrieve(query): return 'optimized retrieval'",
        ]
        llm = MockLLM(responses=responses)
        mutation = RAGArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.rag")
        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "architecture.rag"
        assert result.config.rag_config is not None
        assert "rag_config" in result.components_touched

    async def test_apply_preserves_other_config(
        self, context: MutationContext,
    ) -> None:
        """RAG mutation should not alter system prompt or tools."""
        responses = [
            json.dumps({
                "name": "kb",
                "description": "Knowledge base",
                "mock_output": "context",
                "capability_type": "rag",
            }),
            "def retrieve(q): return 'result'",
        ]
        llm = MockLLM(responses=responses)
        mutation = RAGArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.rag")
        result = await mutation.apply(context, proposal)

        assert result.config.system_prompt == context.config.system_prompt
        assert result.config.tools == context.config.tools


# ---------------------------------------------------------------------------
# Context Architecture Mutation
# ---------------------------------------------------------------------------

class TestContextArchitectureMutation:
    async def test_apply_returns_mutation_result(
        self, context: MutationContext,
    ) -> None:
        responses = [
            json.dumps({
                "name": "user_context",
                "description": "User history context",
                "mock_output": "previous conversation context",
                "capability_type": "context",
            }),
            "def get_context(input): return 'enriched context'",
        ]
        llm = MockLLM(responses=responses)
        mutation = ContextArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.context")
        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "architecture.context"
        assert result.config.context_strategy is not None
        assert "context_strategy" in result.components_touched

    async def test_apply_preserves_other_config(
        self, context: MutationContext,
    ) -> None:
        responses = [
            json.dumps({
                "name": "ctx",
                "description": "Context",
                "mock_output": "context",
                "capability_type": "context",
            }),
            "def ctx(input): return 'context'",
        ]
        llm = MockLLM(responses=responses)
        mutation = ContextArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.context")
        result = await mutation.apply(context, proposal)

        assert result.config.system_prompt == context.config.system_prompt


# ---------------------------------------------------------------------------
# Memory Architecture Mutation
# ---------------------------------------------------------------------------

class TestMemoryArchitectureMutation:
    async def test_apply_returns_mutation_result(
        self, context: MutationContext,
    ) -> None:
        responses = [
            json.dumps({
                "name": "conversation_memory",
                "description": "Track conversation history",
                "mock_output": "remembered context from prior turns",
                "capability_type": "context",
            }),
            "def remember(input): return 'memory'",
        ]
        llm = MockLLM(responses=responses)
        mutation = MemoryArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.memory")
        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "architecture.memory"
        assert result.config.memory_strategy is not None
        assert "memory_strategy" in result.components_touched

    async def test_apply_preserves_other_config(
        self, context: MutationContext,
    ) -> None:
        responses = [
            json.dumps({
                "name": "mem",
                "description": "Memory",
                "mock_output": "memory",
                "capability_type": "context",
            }),
            "def mem(input): return 'memory'",
        ]
        llm = MockLLM(responses=responses)
        mutation = MemoryArchitectureMutation(llm)  # type: ignore[call-arg]

        proposal = _make_proposal("architecture.memory")
        result = await mutation.apply(context, proposal)

        assert result.config.system_prompt == context.config.system_prompt
        assert result.config.tools == context.config.tools
