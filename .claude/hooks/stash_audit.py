#!/usr/bin/env python3
"""PostToolUse/Bash hook: warn if stashes exist that predate the most recent merge."""
# managed by claude-code-starter

import json
import re
import subprocess
import sys


MERGE_PATTERNS = [
    r"git\s+merge\b",
    r"git\s+pull\b",
]


def get_merge_timestamp():
    """Return the Unix timestamp of HEAD (assumed to be the merge commit)."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return None
    return int(result.stdout.strip())


def get_pre_merge_stashes(merge_ts):
    """Return stash entries created before merge_ts."""
    result = subprocess.run(
        ["git", "stash", "list", "--format=%gd|%ct|%s"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    old = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        ref, ts_str, subject = parts
        try:
            ts = int(ts_str)
        except ValueError:
            continue
        if ts < merge_ts:
            old.append(f"  {ref}: {subject}")
    return old


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not any(re.search(p, command) for p in MERGE_PATTERNS):
        return

    tool_result = data.get("tool_result", {})
    stdout = tool_result.get("stdout", "")
    stderr = tool_result.get("stderr", "")
    if "CONFLICT" in stdout or "CONFLICT" in stderr:
        return  # merge didn't complete cleanly — skip audit

    merge_ts = get_merge_timestamp()
    if merge_ts is None:
        return

    stashes = get_pre_merge_stashes(merge_ts)
    if not stashes:
        return

    count = len(stashes)
    label = "stash" if count == 1 else "stashes"
    print(
        f"⚠ Stash audit: {count} {label} created before this merge still "
        f"sitting in the stash list. These may contain work-in-progress that "
        f"was stashed to allow the merge:\n"
        + "\n".join(stashes)
        + "\n\nRun `git stash list` to inspect, `git stash pop` to restore, "
        "or `git stash drop` to discard."
    )


if __name__ == "__main__":
    main()
