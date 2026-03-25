from __future__ import annotations

import importlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def exact_match(actual: str, expected: str, config: dict[str, Any] | None = None) -> float:
    config = config or {}
    if config.get("case_insensitive", False):
        actual = actual.lower()
        expected = expected.lower()
    if config.get("strip_whitespace", True):
        actual = actual.strip()
        expected = expected.strip()
    if config.get("normalize_whitespace", False):
        actual = re.sub(r"\s+", " ", actual)
        expected = re.sub(r"\s+", " ", expected)
    return 1.0 if actual == expected else 0.0


def contains_match(actual: str, expected: str, config: dict[str, Any] | None = None) -> float:
    config = config or {}
    if config.get("case_insensitive", True):
        actual = actual.lower()
        expected = expected.lower()
    return 1.0 if expected in actual else 0.0


def semantic_similarity(
    actual: str, expected: str, config: dict[str, Any] | None = None
) -> float:
    """Semantic similarity via sentence-transformers, falls back to token overlap."""
    config = config or {}
    threshold = config.get("threshold", 0.8)

    try:
        score = _embedding_similarity(actual, expected, config)
    except ImportError:
        logger.debug("sentence-transformers not installed, falling back to token overlap")
        score = _token_overlap(actual, expected)

    return 1.0 if score >= threshold else score / threshold


def tool_call_match(
    actual: str | dict[str, Any],
    expected: str | dict[str, Any],
    config: dict[str, Any] | None = None,
) -> float:
    """Match tool calls by name and optionally by arguments."""
    config = config or {}
    check_args = config.get("check_args", True)

    actual_parsed = _parse_tool_call(actual)
    expected_parsed = _parse_tool_call(expected)

    if actual_parsed is None or expected_parsed is None:
        return 0.0

    if actual_parsed["tool_name"] != expected_parsed["tool_name"]:
        return 0.0

    if not check_args:
        return 1.0

    expected_args = expected_parsed.get("args", {})
    actual_args = actual_parsed.get("args", {})

    if not expected_args:
        return 1.0

    matched = sum(1 for k, v in expected_args.items() if actual_args.get(k) == v)
    return matched / len(expected_args)


def custom_fn(actual: str, expected: str, config: dict[str, Any] | None = None) -> float:
    """Call a user-provided evaluation function."""
    config = config or {}
    fn_path = config.get("fn")
    if not fn_path:
        raise ValueError("custom_fn eval mode requires 'fn' in config")

    module_path, fn_name = fn_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, fn_name)
    return float(fn(actual, expected, config))


METRIC_REGISTRY: dict[str, Any] = {
    "exact_match": exact_match,
    "contains_match": contains_match,
    "semantic_similarity": semantic_similarity,
    "tool_call_match": tool_call_match,
    "custom_fn": custom_fn,
}


def score_output(
    actual: str | dict[str, Any],
    expected: str | dict[str, Any],
    eval_mode: str,
    eval_config: dict[str, Any] | None = None,
) -> float:
    if eval_mode not in METRIC_REGISTRY:
        raise ValueError(f"Unknown eval mode: {eval_mode}. Available: {list(METRIC_REGISTRY)}")
    fn = METRIC_REGISTRY[eval_mode]
    result: float = fn(actual, expected, eval_config)
    return result


def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _embedding_similarity(actual: str, expected: str, config: dict[str, Any]) -> float:
    from sentence_transformers import SentenceTransformer

    model_name = config.get("model", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    embeddings = model.encode([actual, expected])
    cosine = float(
        (embeddings[0] @ embeddings[1])
        / (max(float((embeddings[0] ** 2).sum() ** 0.5), 1e-9)
           * max(float((embeddings[1] ** 2).sum() ** 0.5), 1e-9))
    )
    return cosine


def _parse_tool_call(value: str | dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if "tool_name" in value:
            return value
        return None

    try:
        import json

        parsed = json.loads(value)
        if isinstance(parsed, dict) and "tool_name" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    return None
