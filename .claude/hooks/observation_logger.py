#!/usr/bin/env python3
"""PostToolUse hook: log tool usage patterns to .observations.jsonl for instinct learning."""
# managed by claude-code-starter

import json
import os
import sys
from datetime import datetime


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    log_path = os.path.join(project_dir, ".claude", ".observations.jsonl")

    tool_name = data.get("tool_name", "unknown")
    tool_input = data.get("tool_input", {})

    # Extract useful signals
    observation = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
    }

    # For file operations, log the path
    if tool_name in ("Read", "Edit", "Write"):
        observation["file"] = tool_input.get("file_path", "")
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        # Only log the first 200 chars of command
        observation["command"] = cmd[:200]
    elif tool_name == "Grep":
        observation["pattern"] = tool_input.get("pattern", "")

    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(observation) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    main()
