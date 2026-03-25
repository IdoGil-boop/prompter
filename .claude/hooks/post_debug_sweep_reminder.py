#!/usr/bin/env python3
"""PostToolUse/Edit hook: remind about pattern sweep after bug fixes.

After an Edit or Write operation that looks like a bug fix (based on recent
conversation context or file patterns), reminds the developer to run a
BUGSTONE pattern sweep and update debug docs.
"""
# managed by claude-code-starter

import json
import os
import sys


# File patterns that suggest a bug fix is happening
FIX_INDICATORS = [
    "fix",
    "bug",
    "patch",
    "hotfix",
    "workaround",
    "hack",
]

# Files that are part of the debug workflow itself (skip reminders for these)
DEBUG_DOC_FILES = [
    "gotchas.md",
    "debug-history.md",
]


def is_debug_doc(file_path):
    """Check if the file being edited is a debug doc itself."""
    if not file_path:
        return False
    basename = os.path.basename(file_path)
    return basename in DEBUG_DOC_FILES


def check_branch_name():
    """Check if current branch name suggests a bug fix."""
    try:
        # Read from environment if available
        branch_file = os.path.join(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()),
            ".git", "HEAD"
        )
        if os.path.exists(branch_file):
            with open(branch_file) as f:
                head = f.read().strip()
            if head.startswith("ref: refs/heads/"):
                branch = head[len("ref: refs/heads/"):]
                return any(ind in branch.lower() for ind in FIX_INDICATORS)
    except OSError:
        pass
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Don't remind when editing debug docs themselves
    if is_debug_doc(file_path):
        return

    # Only trigger if we're on a fix branch
    if not check_branch_name():
        return

    print(
        "Bug fix detected (fix branch). Remember:\n"
        "  1. Pattern sweep: grep the codebase for sibling bugs (BUGSTONE)\n"
        "  2. Update docs/gotchas.md if the bug was counter-intuitive\n"
        "  3. Append to docs/debug-history.md with root cause and fix"
    )


if __name__ == "__main__":
    main()
