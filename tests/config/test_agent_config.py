"""Tests for AgentConfig — load/save/diff/hash/with_* round-trips."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec


class TestAgentConfig:
    """AgentConfig immutability, persistence, and builder tests."""

    def test_create_minimal_config(self) -> None:
        config = AgentConfig(system_prompt="Hello")
        assert config.system_prompt == "Hello"
        assert config.tools == {}
        assert config.rag_config is None

    def test_frozen_cannot_mutate(self) -> None:
        config = AgentConfig(system_prompt="Hello")
        with pytest.raises(AttributeError):
            config.system_prompt = "Changed"  # type: ignore[misc]

    def test_save_and_load_round_trip(self) -> None:
        config = AgentConfig(system_prompt="Test prompt\nMulti-line.")
        with tempfile.TemporaryDirectory() as d:
            config.save(Path(d))
            loaded = AgentConfig.load(Path(d))
        assert loaded.system_prompt == config.system_prompt

    def test_save_and_load_with_tools(self) -> None:
        tool = ToolSpec(
            name="search",
            description="Search the web",
            parameters_schema={"type": "object"},
            implementation="def search(): pass",
        )
        config = AgentConfig(system_prompt="Prompt", tools={"search": tool})
        with tempfile.TemporaryDirectory() as d:
            config.save(Path(d))
            loaded = AgentConfig.load(Path(d))
        assert "search" in loaded.tools
        assert loaded.tools["search"].description == "Search the web"

    def test_config_hash_deterministic(self) -> None:
        config = AgentConfig(system_prompt="Same prompt")
        assert config.config_hash() == config.config_hash()

    def test_config_hash_changes_on_mutation(self) -> None:
        config1 = AgentConfig(system_prompt="Prompt A")
        config2 = AgentConfig(system_prompt="Prompt B")
        assert config1.config_hash() != config2.config_hash()

    def test_diff_detects_prompt_change(self) -> None:
        before = AgentConfig(system_prompt="Before")
        after = AgentConfig(system_prompt="After")
        diff = before.diff(after)
        assert "system_prompt" in diff
        assert diff["system_prompt"]["before"] == "Before"
        assert diff["system_prompt"]["after"] == "After"

    def test_diff_empty_when_same(self) -> None:
        config = AgentConfig(system_prompt="Same")
        assert config.diff(config) == {}

    def test_diff_detects_tool_changes(self) -> None:
        tool = ToolSpec(name="t", description="d", parameters_schema={}, implementation="")
        before = AgentConfig(system_prompt="P")
        after = AgentConfig(system_prompt="P", tools={"t": tool})
        diff = before.diff(after)
        assert "tools" in diff
        assert "t" in diff["tools"]["added"]

    def test_with_system_prompt_returns_new_config(self) -> None:
        config = AgentConfig(system_prompt="Old")
        new_config = config.with_system_prompt("New")
        assert new_config.system_prompt == "New"
        assert config.system_prompt == "Old"  # Original unchanged

    def test_with_tool_returns_new_config(self) -> None:
        config = AgentConfig(system_prompt="P")
        tool = ToolSpec(name="t", description="d", parameters_schema={}, implementation="")
        new_config = config.with_tool("t", tool)
        assert "t" in new_config.tools
        assert "t" not in config.tools

    def test_without_tool_returns_new_config(self) -> None:
        tool = ToolSpec(name="t", description="d", parameters_schema={}, implementation="")
        config = AgentConfig(system_prompt="P", tools={"t": tool})
        new_config = config.without_tool("t")
        assert "t" not in new_config.tools
        assert "t" in config.tools

    def test_component_names(self) -> None:
        tool = ToolSpec(name="search", description="d", parameters_schema={}, implementation="")
        config = AgentConfig(system_prompt="P", tools={"search": tool})
        names = config.component_names()
        assert "system_prompt" in names
        assert "tool:search" in names

    def test_load_missing_dir_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            AgentConfig.load("/nonexistent/path")

    def test_load_missing_system_prompt_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d, pytest.raises(
            FileNotFoundError, match="system_prompt.md"
        ):
            AgentConfig.load(d)


class TestToolSpec:
    """ToolSpec serialization tests."""

    def test_to_dict_round_trip(self) -> None:
        spec = ToolSpec(
            name="test",
            description="A test tool",
            parameters_schema={"type": "object"},
            implementation="code",
            enabled=False,
        )
        d = spec.to_dict()
        loaded = ToolSpec.from_dict(d)
        assert loaded.name == spec.name
        assert loaded.description == spec.description
        assert loaded.enabled is False
