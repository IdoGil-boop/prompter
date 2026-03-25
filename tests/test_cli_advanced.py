"""Tests for advanced CLI options (variance-modes, tiers, config file)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from prompter.cli import main
from prompter.config.agent_config import AgentConfig
from prompter.eval.test_suite import TestCase, TestSuite


class TestCLIVarianceModes:
    """Tests for --variance-modes CLI option."""

    def test_optimize_help_shows_variance_modes(self) -> None:
        """optimize --help should show --variance-modes option."""
        runner = CliRunner()
        result = runner.invoke(main, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "--variance-modes" in result.output

    def test_optimize_help_shows_tiers(self) -> None:
        """optimize --help should show --tiers option."""
        runner = CliRunner()
        result = runner.invoke(main, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "--tiers" in result.output

    def test_optimize_help_shows_config(self) -> None:
        """optimize --help should show --config option."""
        runner = CliRunner()
        result = runner.invoke(main, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output


class TestCLITiers:
    """Tests for --tiers CLI option."""

    def test_tiers_option_parses_format(self) -> None:
        """--tiers should accept 'name:provider:model' format."""
        # We test the parsing function directly
        from prompter.cli import _parse_tiers

        result = _parse_tiers("local:ollama:llama3.2,cheap:openai:gpt-4o-mini")
        assert result is not None
        assert "local" in result
        assert result["local"] == {"provider": "ollama", "model": "llama3.2"}
        assert "cheap" in result
        assert result["cheap"] == {"provider": "openai", "model": "gpt-4o-mini"}

    def test_tiers_option_empty_returns_none(self) -> None:
        """Empty --tiers should return None."""
        from prompter.cli import _parse_tiers

        result = _parse_tiers(None)
        assert result is None

    def test_tiers_option_invalid_format_raises(self) -> None:
        """Invalid tier format should raise ValueError."""
        from prompter.cli import _parse_tiers

        with pytest.raises(ValueError, match="Invalid tier format"):
            _parse_tiers("bad_format")


class TestCLIConfigFile:
    """Tests for --config CLI option."""

    def test_config_file_option_in_help(self) -> None:
        """The --config option should appear in help."""
        runner = CliRunner()
        result = runner.invoke(main, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output
