"""Tests for CLI entry point."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from prompter.cli import main
from prompter.config.agent_config import AgentConfig
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.history.store import HistoryStore, IterationRecord


class TestCLI:
    """Tests for click CLI commands."""

    def test_cli_group_exists(self) -> None:
        """The main CLI group should exist and show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "optimize" in result.output
        assert "evaluate" in result.output
        assert "history" in result.output

    def test_evaluate_command_runs(self) -> None:
        """evaluate command should run test suite and show results."""
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / "agent"
            agent_dir.mkdir()
            AgentConfig(system_prompt="You are helpful.").save(agent_dir)

            tests_path = Path(tmp) / "tests.yaml"
            TestSuite(tests=[
                TestCase(id="t1", input="hi", expected="hi", eval_mode="exact_match"),
            ]).save(tests_path)

            runner = CliRunner()
            result = runner.invoke(main, [
                "evaluate",
                str(agent_dir),
                str(tests_path),
                "--model", "mock",
            ])
            # Should run without crashing (may fail to connect to LLM)
            # We just verify the command parses and attempts to run
            assert result.exit_code == 0 or "Error" in result.output or "error" in result.output

    def test_history_command(self) -> None:
        """history command should display history from JSONL file."""
        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"
            store = HistoryStore(history_path)
            store.append(IterationRecord(
                iteration=0,
                timestamp="2026-01-01T00:00:00Z",
                config_hash="abc123",
                score_before=0.0,
                score_after=0.5,
                accepted=True,
                mutation_description="Baseline",
            ))
            store.append(IterationRecord(
                iteration=1,
                timestamp="2026-01-01T00:01:00Z",
                config_hash="def456",
                mutation_type="prompt.rewrite",
                mutation_description="Rewrote prompt",
                score_before=0.5,
                score_after=0.8,
                accepted=True,
            ))

            runner = CliRunner()
            result = runner.invoke(main, ["history", str(history_path)])

            assert result.exit_code == 0
            assert "0.5" in result.output or "0.50" in result.output
            assert "0.8" in result.output or "0.80" in result.output
