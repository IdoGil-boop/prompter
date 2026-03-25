#!/usr/bin/env python3
"""SessionStart hook: verify that hook files referenced in settings.json exist."""
# managed by claude-code-starter

import json
import os
import sys


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    settings_path = os.path.join(project_dir, ".claude", "settings.json")

    if not os.path.exists(settings_path):
        return

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    missing = []
    hooks = settings.get("hooks", {})
    for event, matcher_groups in hooks.items():
        if not isinstance(matcher_groups, list):
            continue
        for group in matcher_groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract script path from command
                for part in cmd.split():
                    cleaned = part.strip('"').replace("$CLAUDE_PROJECT_DIR", project_dir)
                    if cleaned.endswith(".py") or cleaned.endswith(".sh"):
                        if not os.path.exists(cleaned):
                            missing.append(cleaned)

    if missing:
        print(f"Warning: {len(missing)} hook script(s) not found:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)


if __name__ == "__main__":
    # Read stdin (hook provides JSON context)
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    main()
