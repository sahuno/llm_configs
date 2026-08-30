---
name: save-last
description: Save the previous assistant reply to docs/llm_responses/ by running a local extractor. Never retype or Write the previous reply. Use when the user types /save-last.
disable-model-invocation: true
---

A hook may already have saved the file. If so, report that path and stop.

Otherwise run this and print only the path it writes (do **not** reproduce the previous message, do **not** Write it yourself):

```bash
python3 "$HOME/.llm_configs/save_llm_response.py" last --cwd "$PWD"
```
