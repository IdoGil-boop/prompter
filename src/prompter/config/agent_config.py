from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REQUIRED_FILES = ["system_prompt.md"]
OPTIONAL_DIRS = ["tools", "rag", "context", "memory"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    implementation: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
            "implementation": self.implementation,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolSpec:
        return cls(
            name=data["name"],
            description=data["description"],
            parameters_schema=data.get("parameters_schema", {}),
            implementation=data.get("implementation", ""),
            enabled=data.get("enabled", True),
        )


@dataclass(frozen=True)
class AgentConfig:
    """Immutable snapshot of an agent configuration directory."""

    system_prompt: str
    tools: dict[str, ToolSpec] = field(default_factory=dict)
    rag_config: dict[str, Any] | None = None
    context_strategy: dict[str, Any] | None = None
    memory_strategy: dict[str, Any] | None = None

    @classmethod
    def load(cls, path: Path | str) -> AgentConfig:
        root = Path(path)
        if not root.is_dir():
            raise FileNotFoundError(f"Agent config directory not found: {root}")

        prompt_file = root / "system_prompt.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Required file missing: {prompt_file}")

        system_prompt = prompt_file.read_text(encoding="utf-8")
        tools = _load_tools(root / "tools")
        rag_config = _load_yaml_optional(root / "rag" / "config.yaml")
        context_strategy = _load_yaml_optional(root / "context" / "strategy.yaml")
        memory_strategy = _load_yaml_optional(root / "memory" / "strategy.yaml")

        return cls(
            system_prompt=system_prompt,
            tools=tools,
            rag_config=rag_config,
            context_strategy=context_strategy,
            memory_strategy=memory_strategy,
        )

    def save(self, path: Path | str) -> None:
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)

        (root / "system_prompt.md").write_text(self.system_prompt, encoding="utf-8")

        if self.tools:
            tools_dir = root / "tools"
            tools_dir.mkdir(exist_ok=True)
            manifest = {}
            for name, spec in self.tools.items():
                manifest[name] = {
                    "description": spec.description,
                    "parameters_schema": spec.parameters_schema,
                    "enabled": spec.enabled,
                }
                if spec.implementation:
                    (tools_dir / f"{name}.py").write_text(
                        spec.implementation, encoding="utf-8"
                    )
            _save_yaml(tools_dir / "_manifest.yaml", manifest)

        if self.rag_config is not None:
            rag_dir = root / "rag"
            rag_dir.mkdir(exist_ok=True)
            _save_yaml(rag_dir / "config.yaml", self.rag_config)

        if self.context_strategy is not None:
            ctx_dir = root / "context"
            ctx_dir.mkdir(exist_ok=True)
            _save_yaml(ctx_dir / "strategy.yaml", self.context_strategy)

        if self.memory_strategy is not None:
            mem_dir = root / "memory"
            mem_dir.mkdir(exist_ok=True)
            _save_yaml(mem_dir / "strategy.yaml", self.memory_strategy)

    def config_hash(self) -> str:
        content = json.dumps(self._serializable(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def diff(self, other: AgentConfig) -> dict[str, Any]:
        """Return a dict describing what changed between self and other."""
        changes: dict[str, Any] = {}
        if self.system_prompt != other.system_prompt:
            changes["system_prompt"] = {"before": self.system_prompt, "after": other.system_prompt}

        self_tools = set(self.tools.keys())
        other_tools = set(other.tools.keys())
        if self_tools != other_tools or any(
            self.tools[k] != other.tools[k] for k in self_tools & other_tools
        ):
            changes["tools"] = {
                "added": list(other_tools - self_tools),
                "removed": list(self_tools - other_tools),
                "modified": [
                    k for k in self_tools & other_tools if self.tools[k] != other.tools[k]
                ],
            }

        for field_name in ("rag_config", "context_strategy", "memory_strategy"):
            before = getattr(self, field_name)
            after = getattr(other, field_name)
            if before != after:
                changes[field_name] = {"before": before, "after": after}

        return changes

    def component_names(self) -> list[str]:
        components = ["system_prompt"]
        components.extend(f"tool:{name}" for name in self.tools)
        if self.rag_config is not None:
            components.append("rag_config")
        if self.context_strategy is not None:
            components.append("context_strategy")
        if self.memory_strategy is not None:
            components.append("memory_strategy")
        return components

    def with_system_prompt(self, new_prompt: str) -> AgentConfig:
        return AgentConfig(
            system_prompt=new_prompt,
            tools=self.tools,
            rag_config=self.rag_config,
            context_strategy=self.context_strategy,
            memory_strategy=self.memory_strategy,
        )

    def with_tool(self, name: str, spec: ToolSpec) -> AgentConfig:
        new_tools = dict(self.tools)
        new_tools[name] = spec
        return AgentConfig(
            system_prompt=self.system_prompt,
            tools=new_tools,
            rag_config=self.rag_config,
            context_strategy=self.context_strategy,
            memory_strategy=self.memory_strategy,
        )

    def with_rag_config(self, rag_config: dict[str, Any] | None) -> AgentConfig:
        return AgentConfig(
            system_prompt=self.system_prompt,
            tools=self.tools,
            rag_config=rag_config,
            context_strategy=self.context_strategy,
            memory_strategy=self.memory_strategy,
        )

    def with_context_strategy(self, context_strategy: dict[str, Any] | None) -> AgentConfig:
        return AgentConfig(
            system_prompt=self.system_prompt,
            tools=self.tools,
            rag_config=self.rag_config,
            context_strategy=context_strategy,
            memory_strategy=self.memory_strategy,
        )

    def with_memory_strategy(self, memory_strategy: dict[str, Any] | None) -> AgentConfig:
        return AgentConfig(
            system_prompt=self.system_prompt,
            tools=self.tools,
            rag_config=self.rag_config,
            context_strategy=self.context_strategy,
            memory_strategy=memory_strategy,
        )

    def without_tool(self, name: str) -> AgentConfig:
        new_tools = {k: v for k, v in self.tools.items() if k != name}
        return AgentConfig(
            system_prompt=self.system_prompt,
            tools=new_tools,
            rag_config=self.rag_config,
            context_strategy=self.context_strategy,
            memory_strategy=self.memory_strategy,
        )

    def _serializable(self) -> dict[str, Any]:
        return {
            "system_prompt": self.system_prompt,
            "tools": {k: v.to_dict() for k, v in sorted(self.tools.items())},
            "rag_config": self.rag_config,
            "context_strategy": self.context_strategy,
            "memory_strategy": self.memory_strategy,
        }


def _load_tools(tools_dir: Path) -> dict[str, ToolSpec]:
    if not tools_dir.is_dir():
        return {}

    manifest_path = tools_dir / "_manifest.yaml"
    if not manifest_path.exists():
        return {}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}

    tools: dict[str, ToolSpec] = {}
    for name, meta in manifest.items():
        impl_path = tools_dir / f"{name}.py"
        implementation = impl_path.read_text(encoding="utf-8") if impl_path.exists() else ""
        tools[name] = ToolSpec(
            name=name,
            description=meta.get("description", ""),
            parameters_schema=meta.get("parameters_schema", {}),
            implementation=implementation,
            enabled=meta.get("enabled", True),
        )

    return tools


def _load_yaml_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=True)
