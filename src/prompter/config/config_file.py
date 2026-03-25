"""Configuration file support for prompter.yaml."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration from config file."""

    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"


@dataclass
class OptimizerFileConfig:
    """Optimizer configuration from config file."""

    max_iterations: int = 20
    target_score: float = 1.0
    n_eval_runs: int = 3
    variance_modes: list[str] = field(default_factory=lambda: ["run"])


@dataclass
class PrompterConfig:
    """Top-level prompter configuration from config file."""

    agent_dir: str = "./agent"
    test_suite: str = "./tests.yaml"
    optimizer: OptimizerFileConfig = field(default_factory=OptimizerFileConfig)
    llm: LLMConfig | None = None
    tiers: dict[str, dict[str, Any]] | None = None


def load_config(path: Path | str) -> PrompterConfig:
    """Load a prompter.yaml config file.

    Args:
        path: Path to the YAML config file.

    Returns:
        PrompterConfig with parsed values.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    config = PrompterConfig()

    if "agent_dir" in raw:
        config.agent_dir = raw["agent_dir"]
    if "test_suite" in raw:
        config.test_suite = raw["test_suite"]

    # Optimizer section
    if "optimizer" in raw and isinstance(raw["optimizer"], dict):
        opt = raw["optimizer"]
        if "max_iterations" in opt:
            config.optimizer.max_iterations = opt["max_iterations"]
        if "target_score" in opt:
            config.optimizer.target_score = opt["target_score"]
        if "n_eval_runs" in opt:
            config.optimizer.n_eval_runs = opt["n_eval_runs"]
        if "variance_modes" in opt:
            config.optimizer.variance_modes = opt["variance_modes"]

    # LLM section
    if "llm" in raw and isinstance(raw["llm"], dict):
        llm_raw = raw["llm"]
        config.llm = LLMConfig(
            model=llm_raw.get("model", "gpt-4o-mini"),
            api_key_env=llm_raw.get("api_key_env", "OPENAI_API_KEY"),
            base_url=llm_raw.get("base_url", "https://api.openai.com/v1"),
        )

    # Tiers section
    if "tiers" in raw and isinstance(raw["tiers"], dict):
        config.tiers = raw["tiers"]

    return config


def merge_cli_overrides(
    config: PrompterConfig,
    max_iters: int | None = None,
    target_score: float | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    n_runs: int | None = None,
    variance_modes: list[str] | None = None,
) -> PrompterConfig:
    """Merge CLI overrides into a PrompterConfig. CLI values take precedence.

    Args:
        config: Base config from file.
        max_iters: Override max iterations.
        target_score: Override target score.
        model: Override LLM model.
        base_url: Override LLM base URL.
        api_key: Override API key (not stored in config).
        n_runs: Override eval runs.
        variance_modes: Override variance modes.

    Returns:
        New PrompterConfig with overrides applied.
    """
    if max_iters is not None:
        config.optimizer.max_iterations = max_iters
    if target_score is not None:
        config.optimizer.target_score = target_score
    if n_runs is not None:
        config.optimizer.n_eval_runs = n_runs
    if variance_modes is not None:
        config.optimizer.variance_modes = variance_modes

    if model is not None:
        if config.llm is None:
            config.llm = LLMConfig()
        config.llm.model = model
    if base_url is not None:
        if config.llm is None:
            config.llm = LLMConfig()
        config.llm.base_url = base_url

    return config
