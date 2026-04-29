---
description: Answer the question, then save the full answer to ./docs/llm_responses/<timestamp>_<slug>.md
argument-hint: <question>
---

You will answer the user's question below AND persist your full answer to disk so they can review it later.

**Question / topic:**
$ARGUMENTS

## Instructions

1. Answer the question in the normal conversation channel (markdown, as usual).
2. After answering, save an identical copy of your answer as a markdown file:
   - **Directory**: `docs/llm_responses/` (relative to the current working directory). Create it with `mkdir -p` if it does not exist — do NOT put it anywhere else.
   - **Filename**: `<YYYYMMDD>_<HHMMSS>_<slug>.md`
     - Timestamp: use the current local date/time (run `date +%Y%m%d_%H%M%S` via Bash to get the exact value — do not guess).
     - Slug: derive from the topic/question. Lowercase, words joined by `-`, strip punctuation, keep to ≤6 words / ~50 chars.
     - Example: `20260413_142530_clone-repo-and-branch.md`
3. File content structure:
   ```markdown
   ---
   date: <YYYY-MM-DD HH:MM:SS local tz>
   topic: <one-line restatement of the question>
   cwd: <current working directory>
   ---

   # <topic>

   ## Question
   <verbatim $ARGUMENTS>

   ## Answer
   <your full answer, markdown preserved>
   ```
4. Use the Write tool for the file — never `echo >` or heredoc via Bash.
5. After saving, tell the user the absolute path of the file in one short line. Nothing else.

If `$ARGUMENTS` is empty, ask the user what they want answered before proceeding.
