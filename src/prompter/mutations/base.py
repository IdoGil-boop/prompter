from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prompter.config.agent_config import AgentConfig
    from prompter.eval.evaluator import EvalReport
    from prompter.eval.test_suite import TestSuite


@dataclass(frozen=True)
class MutationResult:
    config: AgentConfig
    description: str
    mutation_type: str
    components_touched: list[str]


@dataclass(frozen=True)
class MutationProposal:
    mutation_type: str
    rationale: str
    target_tests: list[str]
    target_components: list[str]
    cost_tier: int
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class MutationContext:
    """Everything a mutation operator needs to make a good decision."""

    config: AgentConfig
    eval_report: EvalReport
    history: list[dict[str, Any]]
    attribution_hints: dict[str, float] = field(default_factory=dict)
    test_suite: TestSuite | None = None


class Mutation(ABC):
    """Base class for all mutation operators."""

    type_id: str
    cost_tier: int

    @abstractmethod
    async def apply(self, context: MutationContext, proposal: MutationProposal) -> MutationResult:
        """Apply this mutation and return a new config."""

    @classmethod
    def registry(cls) -> dict[str, type[Mutation]]:
        return _MUTATION_REGISTRY


_MUTATION_REGISTRY: dict[str, type[Mutation]] = {}


def register_mutation(mutation_class: type[Mutation]) -> type[Mutation]:
    _MUTATION_REGISTRY[mutation_class.type_id] = mutation_class
    return mutation_class
