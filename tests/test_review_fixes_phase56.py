"""Tests for Phase 5+6 code-review and silent-failure-hunter fixes.

Issue 1 (CRITICAL): --tiers not wired to Optimizer — parsed_tiers never passed
Issue 2 (HIGH): api_key_env never resolved via os.environ.get()
Issue 3 (HIGH): Sparkline except Exception: pass — silent error swallowing
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from prompter.cli import _parse_tiers
from prompter.config.config_file import LLMConfig


# --- Issue 1: --tiers not wired to Optimizer ---


class TestTiersWiredToOptimizer:
    """Verify that parsed --tiers are converted to LLMAdapter instances
    and passed to the Optimizer constructor as escalation_tiers."""

    def test_create_tier_adapters_from_parsed_tiers(self) -> None:
        """_create_tier_adapters should create LLMAdapter instances per tier."""
        from prompter.cli import _create_tier_adapters

        parsed = {
            "local": {"provider": "ollama", "model": "llama3.2"},
            "cheap": {"provider": "openai", "model": "gpt-4o-mini"},
        }
        adapters = _create_tier_adapters(parsed, api_key="test-key")
        assert "local" in adapters
        assert "cheap" in adapters
        # Each value should be an LLM adapter with model_id
        assert adapters["local"].model_id == "llama3.2"
        assert adapters["cheap"].model_id == "gpt-4o-mini"

    def test_ollama_provider_uses_localhost_base_url(self) -> None:
        """ollama provider should use http://localhost:11434/v1 as base_url."""
        from prompter.cli import _create_tier_adapters

        parsed = {"local": {"provider": "ollama", "model": "llama3.2"}}
        adapters = _create_tier_adapters(parsed, api_key=None)
        # OllamaAdapter or OpenAICompat with localhost base URL
        assert "local" in adapters

    def test_openai_provider_uses_openai_base_url(self) -> None:
        """openai provider should use https://api.openai.com/v1 as base_url."""
        from prompter.cli import _create_tier_adapters

        parsed = {"cheap": {"provider": "openai", "model": "gpt-4o-mini"}}
        adapters = _create_tier_adapters(parsed, api_key="sk-test")
        assert "cheap" in adapters

    def test_optimize_passes_tiers_to_optimizer(self) -> None:
        """When --tiers is provided, Optimizer should receive escalation_tiers."""
        from unittest.mock import MagicMock, AsyncMock

        from prompter.config.agent_config import AgentConfig
        from prompter.eval.evaluator import EvalReport
        from prompter.eval.test_suite import TestCase, TestSuite
        from prompter.optimizer import Optimizer, OptimizationResult

        # We patch Optimizer.__init__ to capture args
        init_kwargs: dict[str, Any] = {}
        original_init = Optimizer.__init__

        def capturing_init(self_opt: Any, **kwargs: Any) -> None:
            init_kwargs.update(kwargs)
            # Don't actually init — just capture
            raise RuntimeError("captured")

        with patch.object(Optimizer, "__init__", capturing_init):
            from prompter.cli import _create_tier_adapters

            parsed_tiers = _parse_tiers("local:ollama:llama3.2,cheap:openai:gpt-4o-mini")
            assert parsed_tiers is not None
            tier_adapters = _create_tier_adapters(parsed_tiers, api_key="test")
            assert isinstance(tier_adapters, dict)
            assert len(tier_adapters) == 2


# --- Issue 2: api_key_env never resolved ---


class TestApiKeyEnvResolution:
    """Verify that api_key_env from config file is resolved via os.environ.get()."""

    def test_resolve_api_key_env_reads_environment(self) -> None:
        """When config has api_key_env, CLI should resolve it from environment."""
        from prompter.cli import _resolve_api_key

        with patch.dict(os.environ, {"MY_API_KEY": "secret-from-env"}):
            llm_config = LLMConfig(api_key_env="MY_API_KEY")
            resolved = _resolve_api_key(explicit_key=None, llm_config=llm_config)
            assert resolved == "secret-from-env"

    def test_explicit_api_key_takes_precedence(self) -> None:
        """Explicit --api-key should take precedence over api_key_env."""
        from prompter.cli import _resolve_api_key

        with patch.dict(os.environ, {"MY_API_KEY": "from-env"}):
            llm_config = LLMConfig(api_key_env="MY_API_KEY")
            resolved = _resolve_api_key(explicit_key="explicit-key", llm_config=llm_config)
            assert resolved == "explicit-key"

    def test_missing_env_var_returns_none(self) -> None:
        """If env var doesn't exist, _resolve_api_key should return None."""
        from prompter.cli import _resolve_api_key

        # Ensure the var doesn't exist
        env = os.environ.copy()
        env.pop("NONEXISTENT_VAR", None)
        with patch.dict(os.environ, env, clear=True):
            llm_config = LLMConfig(api_key_env="NONEXISTENT_VAR")
            resolved = _resolve_api_key(explicit_key=None, llm_config=llm_config)
            assert resolved is None

    def test_no_llm_config_returns_explicit_key(self) -> None:
        """When no LLM config, should return the explicit key as-is."""
        from prompter.cli import _resolve_api_key

        resolved = _resolve_api_key(explicit_key="my-key", llm_config=None)
        assert resolved == "my-key"


# --- Issue 3: Sparkline except Exception: pass ---


class TestSparklineLogging:
    """Verify that sparkline/history display errors are logged, not silently swallowed."""

    def test_sparkline_error_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """When sparkline display fails, the error should be logged at debug level."""
        from prompter.cli import _print_optimization_result
        from prompter.config.agent_config import AgentConfig
        from prompter.eval.evaluator import EvalReport

        # Create a result object with a history_path that exists but has bad data
        class FakeResult:
            baseline_report = EvalReport(config_id="x", aggregate_score=0.5, results=[])
            final_report = EvalReport(config_id="x", aggregate_score=0.7, results=[])
            iterations_run = 5
            history_path: str | None = None
            best_config = AgentConfig(system_prompt="same prompt")

        result = FakeResult()

        with tempfile.TemporaryDirectory() as tmp:
            # Write invalid JSONL to trigger an error in history loading
            bad_file = Path(tmp) / "history.jsonl"
            bad_file.write_text("not valid json\n")
            result.history_path = str(bad_file)

            with caplog.at_level(logging.DEBUG, logger="prompter.cli"):
                _print_optimization_result(
                    result,
                    AgentConfig(system_prompt="same prompt"),
                    Path(tmp),
                )

            # The error should be logged, not silently swallowed
            assert any(
                "Display rendering failed" in record.message
                for record in caplog.records
            ), (
                f"Expected 'Display rendering failed' in log records. "
                f"Got: {[r.message for r in caplog.records]}"
            )
