<!-- managed by claude-code-starter -->
# Hooks Authoring

Write and maintain Claude Code hooks in `.claude/settings.json`.

## Format

Hooks have three levels: **event** → **matcher group** → **hooks array**.

```json
{
  "hooks": {
    "<Event>": [
      {
        "matcher": "<regex or omit for all>",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/my-script.py"
          }
        ]
      }
    ]
  }
}
```

## Common Events

| Event | Matcher filters on | Example matchers |
|-------|-------------------|-----------------|
| `SessionStart` | how session started | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | exit reason | `clear`, `logout`, `prompt_input_exit` |
| `PreToolUse` | tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| `PostToolUse` | tool name | `Write`, `Edit\|Write` |
| `Stop` | (no matcher) | always fires |

## Hook Types

- **`command`** — shell script. Receives JSON on stdin, returns via exit code + stdout.
- **`prompt`** — single-turn LLM evaluation. Returns `{ "ok": true/false, "reason": "..." }`.
- **`agent`** — multi-turn subagent with tool access.

## Script Conventions

- Use `$CLAUDE_PROJECT_DIR` for project-relative paths
- Scripts read hook JSON from stdin: `json.load(sys.stdin)`
- Exit 0 = success, Exit 2 = block (with stderr as reason)
- Only Python stdlib or bash — no external dependencies
- Create scripts in `.claude/hooks/`

## Gotchas

- **Old format won't load**: hooks must be nested inside `{ "hooks": [...] }`
- **Disabling**: set `"disableAllHooks": true` in settings.json
- **Changes require restart**: hooks are snapshotted at session start
