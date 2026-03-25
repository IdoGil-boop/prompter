"""Tests for ConfigSnapshot — create/save/load."""
from __future__ import annotations

import tempfile
from pathlib import Path

from prompter.config.agent_config import AgentConfig
from prompter.config.snapshot import ConfigSnapshot


class TestConfigSnapshot:
    def test_create_snapshot(self) -> None:
        config = AgentConfig(system_prompt="Test")
        snapshot = ConfigSnapshot.create(config, iteration=5)
        assert snapshot.iteration == 5
        assert snapshot.snapshot_id == config.config_hash()
        assert snapshot.config is config

    def test_save_and_load_round_trip(self) -> None:
        config = AgentConfig(system_prompt="Snapshot test prompt")
        snapshot = ConfigSnapshot.create(config, iteration=3)

        with tempfile.TemporaryDirectory() as d:
            snapshots_dir = Path(d)
            saved_path = snapshot.save(snapshots_dir)
            loaded = ConfigSnapshot.load(saved_path)

        assert loaded.snapshot_id == snapshot.snapshot_id
        assert loaded.iteration == 3
        assert loaded.config.system_prompt == "Snapshot test prompt"
