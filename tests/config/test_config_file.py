"""Tests for config file loading and merging."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from prompter.config.config_file import PrompterConfig, load_config, merge_cli_overrides


class TestConfigFileLoading:
    """Tests for loading prompter.yaml config files."""

    def test_load_basic_config(self) -> None:
        """Should load a basic prompter.yaml config."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "prompter.yaml"
            config_path.write_text(
                yaml.dump({
                    "agent_dir": "./my-agent",
                    "test_suite": "./tests.yaml",
                    "optimizer": {
                        "max_iterations": 30,
                        "target_score": 0.95,
                    },
                }),
                encoding="utf-8",
            )

            config = load_config(config_path)
            assert config.agent_dir == "./my-agent"
            assert config.test_suite == "./tests.yaml"
            assert config.optimizer.max_iterations == 30
            assert config.optimizer.target_score == 0.95

    def test_load_config_with_llm(self) -> None:
        """Should load LLM configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "prompter.yaml"
            config_path.write_text(
                yaml.dump({
                    "agent_dir": "./agent",
                    "test_suite": "./tests.yaml",
                    "llm": {
                        "model": "gpt-4o-mini",
                        "api_key_env": "OPENAI_API_KEY",
                        "base_url": "https://api.openai.com/v1",
                    },
                }),
                encoding="utf-8",
            )

            config = load_config(config_path)
            assert config.llm is not None
            assert config.llm.model == "gpt-4o-mini"
            assert config.llm.api_key_env == "OPENAI_API_KEY"
            assert config.llm.base_url == "https://api.openai.com/v1"

    def test_load_config_with_tiers(self) -> None:
        """Should load tier configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "prompter.yaml"
            config_path.write_text(
                yaml.dump({
                    "agent_dir": "./agent",
                    "test_suite": "./tests.yaml",
                    "tiers": {
                        "local": {"model": "llama3.2", "provider": "ollama"},
                        "cheap": {"model": "gpt-4o-mini", "provider": "openai"},
                    },
                }),
                encoding="utf-8",
            )

            config = load_config(config_path)
            assert config.tiers is not None
            assert "local" in config.tiers
            assert config.tiers["local"]["model"] == "llama3.2"
            assert config.tiers["cheap"]["provider"] == "openai"

    def test_load_config_with_variance_modes(self) -> None:
        """Should load optimizer config with variance modes."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "prompter.yaml"
            config_path.write_text(
                yaml.dump({
                    "agent_dir": "./agent",
                    "test_suite": "./tests.yaml",
                    "optimizer": {
                        "variance_modes": ["run", "order"],
                    },
                }),
                encoding="utf-8",
            )

            config = load_config(config_path)
            assert config.optimizer.variance_modes == ["run", "order"]

    def test_load_nonexistent_file_raises(self) -> None:
        """Should raise FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/prompter.yaml"))

    def test_default_config_values(self) -> None:
        """Config should have sensible defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "prompter.yaml"
            config_path.write_text(
                yaml.dump({
                    "agent_dir": "./agent",
                    "test_suite": "./tests.yaml",
                }),
                encoding="utf-8",
            )

            config = load_config(config_path)
            assert config.optimizer.max_iterations == 20
            assert config.optimizer.target_score == 1.0
            assert config.optimizer.n_eval_runs == 3


class TestCLIOverrides:
    """Tests for CLI args overriding config file values."""

    def test_cli_overrides_max_iters(self) -> None:
        """CLI --max-iters should override config file value."""
        config = PrompterConfig(
            agent_dir="./agent",
            test_suite="./tests.yaml",
        )
        merged = merge_cli_overrides(config, max_iters=50)
        assert merged.optimizer.max_iterations == 50

    def test_cli_overrides_model(self) -> None:
        """CLI --model should override config file LLM model."""
        config = PrompterConfig(
            agent_dir="./agent",
            test_suite="./tests.yaml",
        )
        merged = merge_cli_overrides(config, model="gpt-4o")
        assert merged.llm is not None
        assert merged.llm.model == "gpt-4o"

    def test_cli_none_values_dont_override(self) -> None:
        """CLI None values should not override config file values."""
        config = PrompterConfig(
            agent_dir="./agent",
            test_suite="./tests.yaml",
        )
        config.optimizer.max_iterations = 30
        merged = merge_cli_overrides(config, max_iters=None)
        assert merged.optimizer.max_iterations == 30
