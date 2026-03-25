#!/usr/bin/env python3
"""PreToolUse/Bash hook: clean build caches before debug reproduction.

Detects common cache directories that cause stale-state bugs and removes them
so that reproduction happens in a clean environment. Only triggers when the
Bash command looks like a test/run/dev command (not arbitrary shell usage).
"""
# managed by claude-code-starter

import json
import os
import re
import shutil
import sys


# Commands that suggest the user is reproducing a bug
REPRO_PATTERNS = [
    r"npm\s+(run|start|test|dev)",
    r"yarn\s+(start|test|dev)",
    r"pnpm\s+(run|start|test|dev)",
    r"npx\s+",
    r"python\s+(-m\s+)?(pytest|unittest)",
    r"pytest\b",
    r"cargo\s+(test|run)",
    r"go\s+(test|run)",
    r"mix\s+test",
    r"bundle\s+exec\s+r(spec|ails)",
]

# Cache directories to clean (relative to project root)
CACHE_DIRS = [
    ".next",
    "dist",
    "build",
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".turbo",
    ".parcel-cache",
    ".nuxt",
    ".output",
]


def find_project_root():
    """Walk up from CWD to find project root (has package.json, pyproject.toml, etc.)."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return cwd


def clean_caches(project_root):
    """Remove stale cache directories. Returns list of cleaned dirs."""
    cleaned = []
    for cache_dir in CACHE_DIRS:
        full_path = os.path.join(project_root, cache_dir)
        if os.path.isdir(full_path):
            try:
                shutil.rmtree(full_path)
                cleaned.append(cache_dir)
            except OSError:
                pass  # Permission denied or in use — skip silently

    # Also clean nested __pycache__ dirs
    for root, dirs, _ in os.walk(project_root):
        # Skip node_modules and .git
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".venv", "venv")]
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                rel = os.path.relpath(pycache_path, project_root)
                cleaned.append(rel)
            except OSError:
                pass

    return cleaned


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only trigger on reproduction-like commands
    is_repro = any(re.search(p, command) for p in REPRO_PATTERNS)
    if not is_repro:
        return

    project_root = find_project_root()
    cleaned = clean_caches(project_root)

    if cleaned:
        dirs_str = ", ".join(cleaned[:5])
        extra = f" (+{len(cleaned) - 5} more)" if len(cleaned) > 5 else ""
        print(f"Debug cleanup: removed {dirs_str}{extra} for clean reproduction.")


if __name__ == "__main__":
    main()
