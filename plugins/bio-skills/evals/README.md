# Trigger tests for bio-skills

Each folder is one test: a request written the way Samuel would type it
(`prompt.md`), and a check that the matching skill was actually loaded
(`graders/skill-fired.md`). They exist because a skill whose one-line
description does not match real phrasing never loads, and nothing tells you.

Run all of them once each (about $2.25 and two minutes on 2026-10-31):

```bash
claude plugin eval plugins/bio-skills --ablation none --runs 1 -j 4 --max-cost-usd 5 --no-publish
```

Run after any change to a skill's `description:`. A score of 0 means the skill
did not load from that request; reword the description, not the test.

The check matches the skill by name, so a different skill loading does not
count as a pass (confirmed with a deliberate wrong-name control, 2026-10-31).
