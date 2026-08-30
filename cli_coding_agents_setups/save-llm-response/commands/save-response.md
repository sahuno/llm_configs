---
description: Answer a question; a Stop hook or /save-last persists it to docs/llm_responses/ (do not Write a second copy)
argument-hint: <question>
disable-model-invocation: true
---

Answer the question below in the normal conversation channel. Do **not** use Write/Bash to save it.

A Stop hook (Claude, Grok) copies the answer to `docs/llm_responses/`. If this harness has no Stop hook, tell the user to run `/save-last` after the answer — one short line, only if you are unsure the hook exists.

**Question:**
$ARGUMENTS
