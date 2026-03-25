#!/usr/bin/env python3
"""SessionEnd hook: remind to run /maintain if there are uncommitted changes."""
# managed by claude-code-starter

import json
import subprocess
import sys


def main():
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print("Reminder: You have uncommitted changes. Consider running /maintain to capture session learnings.")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    main()
