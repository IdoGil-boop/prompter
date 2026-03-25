#!/usr/bin/env python3
"""PostToolUse/Bash hook: detect git merge operations and remind to run tests."""
# managed by claude-code-starter

import json
import re
import sys


MERGE_PATTERNS = [
    r"git\s+merge",
    r"git\s+pull",
    r"git\s+stash\s+pop",
    r"git\s+stash\s+apply",
    r"git\s+rebase",
    r"git\s+cherry-pick",
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    for pattern in MERGE_PATTERNS:
        if re.search(pattern, command):
            print(
                "Merge operation detected. Remember to run tests to verify nothing broke."
            )
            return


if __name__ == "__main__":
    main()
