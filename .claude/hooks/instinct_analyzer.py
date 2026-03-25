#!/usr/bin/env python3
"""SessionEnd hook: analyze observation log for patterns and create instinct YAML files."""
# managed by claude-code-starter

import json
import os
import sys
from collections import Counter
from datetime import datetime


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    log_path = os.path.join(project_dir, ".claude", ".observations.jsonl")

    if not os.path.exists(log_path):
        return

    # Read observations
    observations = []
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        observations.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return

    if len(observations) < 10:
        return  # Not enough data for pattern detection

    # Count tool usage patterns
    tool_counts = Counter(obs.get("tool", "") for obs in observations)

    # Count file access patterns
    file_counts = Counter(
        obs.get("file", "").rsplit("/", 1)[-1]
        for obs in observations
        if obs.get("file")
    )

    # Log summary (for future instinct creation by /maintain)
    summary_path = os.path.join(project_dir, ".claude", ".pattern_summary.json")
    summary = {
        "analyzed_at": datetime.utcnow().isoformat(),
        "observation_count": len(observations),
        "top_tools": dict(tool_counts.most_common(5)),
        "top_files": dict(file_counts.most_common(10)),
    }

    try:
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
    except OSError:
        pass

    # Clear observations log (reset for next session)
    try:
        open(log_path, "w").close()
    except OSError:
        pass


if __name__ == "__main__":
    main()
