# Claude Code status line

Custom status line that renders:

```
zsh:<host>:<cwd> | <model display name> | ctx:<N>%
```

Example: `zsh:LSKI4321:/Users/ahunos/personal/PersonalizeClaude/llm_configs | Opus 4.6 (1M context) | ctx:8%`

## Install on a new machine

1. Copy the script into `~/.claude/` and make it executable:
   ```bash
   cp statusline-command.sh ~/.claude/statusline-command.sh
   chmod +x ~/.claude/statusline-command.sh
   ```
2. Add the `statusLine` block to `~/.claude/settings.json`:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "sh ~/.claude/statusline-command.sh"
     }
   }
   ```
3. Ensure `jq` is installed (script uses it to parse the JSON piped in on stdin):
   ```bash
   # macOS
   brew install jq
   # Debian/Ubuntu
   sudo apt-get install -y jq
   ```
4. Restart Claude Code — the new status line appears at the bottom of the TUI.

## How it works

Claude Code pipes a JSON blob (session info, cwd, model, context window usage)
to the status-line command on stdin every ~300 ms. Whatever the script prints
to stdout becomes the status line. See
https://docs.anthropic.com/en/docs/claude-code/statusline for the full schema.
