from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prompter.config.agent_config import AgentConfig

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigSnapshot:
    """A named, hashable checkpoint of an agent config."""

    config: AgentConfig
    snapshot_id: str
    iteration: int

    @classmethod
    def create(cls, config: AgentConfig, iteration: int) -> ConfigSnapshot:
        return cls(
            config=config,
            snapshot_id=config.config_hash(),
            iteration=iteration,
        )

    def save(self, snapshots_dir: Path) -> Path:
        out_dir = snapshots_dir / self.snapshot_id
        self.config.save(out_dir)
        meta = {"snapshot_id": self.snapshot_id, "iteration": self.iteration}
        (out_dir / "_snapshot_meta.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        return out_dir

    @classmethod
    def load(cls, snapshot_dir: Path) -> ConfigSnapshot:
        meta_path = snapshot_dir / "_snapshot_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        config = AgentConfig.load(snapshot_dir)
        return cls(
            config=config,
            snapshot_id=meta["snapshot_id"],
            iteration=meta["iteration"],
        )
