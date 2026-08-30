# save-last CLI (optional)

Grok and Claude Code already have a native `/copy`. Prefer that:

```text
# Grok
/copy docs/llm_responses/last.md
/copy 2 path.md

# Claude Code
/copy          then press w → filename
/copy 2        then press w → filename
/export file.md   # whole conversation
```

Those are client builtins (no extra hook process, no model tokens).

This directory is an optional CLI for harnesses without `/copy` (Codex, OpenCode):

```bash
python3 ~/.llm_configs/save_llm_response.py last
```

`install.sh` copies the script to `~/.llm_configs/` only. It does **not** register hooks.
