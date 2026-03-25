from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

EvalMode = Literal[
    "exact_match",
    "contains_match",
    "semantic_similarity",
    "tool_call_match",
    "custom_fn",
]


@dataclass(frozen=True)
class TestCase:
    id: str
    input: str
    expected: str | dict[str, Any]
    eval_mode: EvalMode
    eval_config: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        return cls(
            id=data["id"],
            input=data["input"],
            expected=data["expected"],
            eval_mode=data.get("eval", "exact_match"),
            eval_config=data.get("config", {}),
            weight=data.get("weight", 1.0),
            tags=data.get("tags", []),
            context=data.get("context"),
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "input": self.input,
            "expected": self.expected,
            "eval": self.eval_mode,
        }
        if self.eval_config:
            d["config"] = self.eval_config
        if self.weight != 1.0:
            d["weight"] = self.weight
        if self.tags:
            d["tags"] = self.tags
        if self.context is not None:
            d["context"] = self.context
        return d


@dataclass
class TestSuite:
    tests: list[TestCase]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str) -> TestSuite:
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "tests" not in data:
            raise ValueError(f"Test suite must have a 'tests' key: {path}")

        tests = [TestCase.from_dict(t) for t in data["tests"]]
        metadata = {k: v for k, v in data.items() if k != "tests"}

        logger.info("Loaded %d test cases from %s", len(tests), path)
        return cls(tests=tests, metadata=metadata)

    def save(self, path: Path | str) -> None:
        path = Path(path)
        data: dict[str, Any] = {**self.metadata, "tests": [t.to_dict() for t in self.tests]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def filter_by_tags(self, tags: list[str]) -> TestSuite:
        tag_set = set(tags)
        filtered = [t for t in self.tests if tag_set & set(t.tags)]
        return TestSuite(tests=filtered, metadata=self.metadata)

    @property
    def total_weight(self) -> float:
        return sum(t.weight for t in self.tests)
