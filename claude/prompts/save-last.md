---
description: Save your most recent assistant message to ./docs/llm_responses/<timestamp>_<slug>.md
---

Save your most recent assistant reply in this conversation (the turn immediately before this command) to disk.

## Instructions

1. Identify the content to save: the text of your previous assistant message in the current conversation. Reproduce it verbatim — do not rewrite, summarize, or "improve" it. If the previous turn was itself a slash command or an empty turn, ask the user which turn they want saved and stop.
2. Derive a topic/slug from that reply: pick a concise description of what the reply was about (≤6 words, lowercase, `-`-joined, stripped of punctuation, ≤50 chars).
3. Determine the destination:
   - **Directory**: `docs/llm_responses/` (relative to the current working directory). Create it with `mkdir -p` if it does not exist.
   - **Filename**: `<YYYYMMDD>_<HHMMSS>_<slug>.md`
     - Use `date +%Y%m%d_%H%M%S` via Bash for the timestamp — do not guess.
     - Example: `20260413_142530_mcp-frequent-list.md`
4. Write the file with this structure using the Write tool:
   ```markdown
   ---
   date: <YYYY-MM-DD HH:MM:SS local tz>
   topic: <slug's expansion — one line>
   cwd: <current working directory>
   source: save-last (previous assistant turn)
   ---

   # <topic>

   <verbatim previous assistant message, markdown preserved>
   ```
5. After saving, reply with a single short line giving the absolute path of the saved file. Nothing else.
