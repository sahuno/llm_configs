---
description: Save the previous assistant reply to docs/llm_responses/ (extractor copies the transcript; the model must not re-emit it)
disable-model-invocation: true
---

A hook may already have saved the file. If so, report that path and stop.

Otherwise run this and print only the path it writes (do **not** reproduce the previous message, do **not** Write it yourself):

```bash
python3 "$HOME/.llm_configs/save_llm_response.py" last --cwd "$PWD"
```
