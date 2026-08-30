---
name: save-response
description: Answer a question once. A hook or /save-last persists it to docs/llm_responses/. Do not Write a second copy. Use when the user types /save-response.
argument-hint: <question>
disable-model-invocation: true
---

Answer the question below in the normal conversation channel. Do **not** use Write/Bash to save it.

A Stop hook (Claude, Grok) copies `last_assistant_message` to `docs/llm_responses/` when this command is installed. If this harness has no Stop hook, tell the user to run `/save-last` after the answer — one short line, only if you are unsure the hook exists.

**Question:**
$ARGUMENTS
