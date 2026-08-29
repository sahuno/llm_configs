# Claude Code environment variables

Portable reference for Claude Code environment variables so a new machine can
be bootstrapped quickly.

## Files
- `claude_env.template.sh` — committed, documented template of every env var with
  a one-line description. Safe to share.
- `claude_env.local.sh` — **not committed** (gitignored). Holds real values
  (API keys, tokens). Create by copying the template.

## Bootstrap on a new machine
```bash
cp claude_env.template.sh claude_env.local.sh
# edit claude_env.local.sh — uncomment and fill in the vars you need
echo '[ -f ~/personal/PersonalizeClaude/llm_configs/claude/profiles/env/claude_env.local.sh ] && source ~/personal/PersonalizeClaude/llm_configs/claude/profiles/env/claude_env.local.sh' >> ~/.zshrc
source ~/.zshrc
```

## Reference
Official docs: https://docs.anthropic.com/en/docs/claude-code/settings
