---
project: llm_configs
status: active
owner: Samuel Ahuno
team: Samuel only
next_action: Confirm symlink survives a /config write; classify the cloud_sync_destination.md site path before committing it
blockers: none
updated: 2026-09-21
shared_copy: none
---

# llm_configs

Shared principles, plugins and profiles for coding and HPC agents (bio-skills, bio-guardrails, hpc-site), loaded at project start (https://github.com/sahuno/llm_configs).

Where it stands, as compiled 2026-09-18 on the project page: Plugin marketplace for bio-skills, bio-guardrails and hpc-site. On 2026-08-30 all three were reinstalled after two had dropped off, and PR #19 bumped versions. On 2026-09-03 cleanupPeriodDays was set to 36500 so Claude Code transcripts stop expiring after 30 days. (Agent, 2026-09-03.) Two sources disagree on the branch and neither was re-checked here: the page text says "Current branch lab-figure-composer" (2026-09-03), while the Board's compiled status block says `figure-style-consolidation`, last commit 2026-09-06, 2 dirty (2026-09-18).

This ledger was seeded on 2026-09-18 from `/Users/sahuno/projects/personal/secondBrain/wiki/projects/llm_configs.md` (compiled 2026-09-18) and `/Users/sahuno/projects/personal/secondBrain/state/projects.csv`. Nothing in it was re-measured; correct anything stale.

## Exact next steps

1. Load at project start; no next feature is queued (state/projects.csv, 2026-08-18).

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|

## Decisions

- 2026-09-03 · `cleanupPeriodDays` set to 36500 · because Claude Code transcripts were silently expiring after 30 days on the built-in default · by Samuel

## Log

### 2026-09-21 09:55 · Claude (Opus 5) · Pushed 32c340a; ledger itself now tracked
- **Done:** Pushed the settings-tracking commit to origin/figure-style-consolidation (4b6e1a2..32c340a). Committed PROGRESS.md into the repo at the users request. Could not settle whether Claude Codes own settings writes preserve the symlink: there is no "claude config set" subcommand in 2.1.278 -- "claude config" is parsed as a prompt and spawned a nested session instead -- and /config is interactive only, so the test needs a human. Ran tools/audit_site_paths.sh: it exits 1 on one unreviewed line in the untracked plugins/hpc-site/skills/mskcc-hpc/references/cloud_sync_destination.md. That file is not committed, so the pushed branch is unaffected, but it will fail CI when committed.
- **Key paths:** PROGRESS.md (now tracked); tools/audit_site_paths.sh (run, not changed); plugins/hpc-site/skills/mskcc-hpc/references/cloud_sync_destination.md (untracked, fails the audit)
- **Commands that worked:** git push origin figure-style-consolidation; ./tools/audit_site_paths.sh; echo $?  # 1, not 0 -- piping to tail masks it
- **Known issues / blockers:** Open: does a settings write from inside Claude Code replace the symlink at ~/.claude/settings.json? Needs one interactive /config change, then: ls -la ~/.claude/settings.json (expect ->). Also open: cloud_sync_destination.md has one unreviewed site path and will fail tools/audit_site_paths.sh in CI once committed; classify it in docs/site-path-allowlist.tsv first.
- **Exact next steps:** 1. After the next /config change, run ls -la ~/.claude/settings.json to confirm the symlink survived. 2. Before committing cloud_sync_destination.md, classify its site path in docs/site-path-allowlist.tsv so the audit passes. 3. plugins/hpc-site/skills/mskcc-hpc/SKILL.md is still modified and uncommitted.

### 2026-09-21 09:51 · Claude (Opus 5) · settings.json and statusline.sh now tracked in the repo via symlinks
- **Done:** claude/settings.json was a hand-copied snapshot from 2026-08-29 and had drifted (still had alwaysThinkingEnabled and a bell Notification hook; missing the ledger hooks, plugin list, model effort levels and statusLine). Replaced it with the live file and symlinked ~/.claude/settings.json -> claude/settings.json so they cannot diverge again. Did the same for ~/.claude/statusline.sh -> claude/statusline.sh, which settings.json references and which was not in the repo at all. Both READMEs corrected (claude/README.md had claimed nothing here needs syncing). Committed as 32c340a; git stores contents, not links (mode 100644/100755, verified). Left the three pre-existing dirty files untouched. NOT pushed.
- **Key paths:** claude/settings.json; claude/statusline.sh (new); claude/README.md; README.md; ~/.claude/settings.json and ~/.claude/statusline.sh are now symlinks into the repo
- **Commands that worked:** cp ~/.claude/settings.json claude/settings.json; ln -s $PWD/claude/settings.json ~/.claude/.settings.json.newlink && mv -f ~/.claude/.settings.json.newlink ~/.claude/settings.json; git ls-files -s claude/settings.json  # expect 100644, not 120000
- **Known issues / blockers:** Repo is PUBLIC, so these settings are now public; checked and they contain no keys or tokens, only config and /Users/sahuno paths. Hook commands are absolute paths into /Users/sahuno/.local/bin (from the singularity repo) and will not resolve on another machine. Unverified: whether Claude Code writing settings itself (via /config etc.) resolves the symlink or replaces it -- the binary contains both a "Writing through symlink" path and a "Refusing to write through symlink" path and strings alone did not settle which applies. Check with: ls -la ~/.claude/settings.json (expect an arrow, not a regular file).
- **Exact next steps:** 1. Optional: push 32c340a to origin/figure-style-consolidation. 2. Optional: commit PROGRESS.md, still untracked. 3. After any settings change made from inside Claude Code, run ls -la ~/.claude/settings.json to confirm the symlink survived.

### 2026-09-21 09:46 · Claude (Opus 5) · Status line now refreshes on a timer, not only on events
- **Done:** Diagnosed the frozen "assistant:1s ago" label in the custom status line. It is not a Claude Code bug: statusLine has exactly one type ("command"), its stdout is rendered in the terminal only and never enters a prompt (so it costs zero tokens), and without a refreshInterval the CLI re-runs the command only on events (lastAssistantMessageId, tokenUsage, permissionMode, vimMode, mainLoopModel, fastMode, effortValue, thinkingEnabled, prStatus) -- elapsed time is not among them, so the relative timestamp froze between turns. Added "refreshInterval": 5 to the statusLine block. User confirmed it ticks; statusLine settings therefore hot-reload with no restart. Also benchmarked the script (86 ms/run, dominated by ~10 process spawns, not the 28 ms whole-file jq over the transcript); wrote an optimised variant at 61 ms but did NOT install it -- not worth the churn at a 5 s interval.
- **Key paths:** ~/.claude/settings.json (changed; backup ~/.claude/settings.json.bak-20260921-094518); ~/.claude/statusline.sh (unchanged); optimised variant left in session scratchpad only, not installed
- **Commands that worked:** cp ~/.claude/settings.json ~/.claude/settings.json.bak-$(date +%Y%m%d-%H%M%S); jq ".statusLine.refreshInterval = 5" ~/.claude/settings.json > new && jq empty new && mv new ~/.claude/settings.json; diff <(jq -S . ~/.claude/settings.json.bak-20260921-094518) <(jq -S . ~/.claude/settings.json)
- **Known issues / blockers:** None open. Note ~/.claude/settings.json is NOT tracked in this repo, so this change does not survive a fresh machine unless it is added to the repo. Older backups from Aug 2026 show a different config (model claude-fable-5[1m], no ledger hooks) -- left untouched.
- **Exact next steps:** 1. Optional: decide whether ~/.claude/settings.json should be version-controlled in this repo so status line + hooks config is reproducible. 2. Nothing else queued.

### 2026-09-18 23:17 · Claude (Opus 5), seeding · Ledger seeded from the second brain
- **Done:** created from wiki/projects/llm_configs.md (compiled 2026-09-18) and state/projects.csv; no code or data changed
- **Key paths:** /Users/sahuno/projects/llm_configs/PROGRESS.md; /Users/sahuno/projects/personal/secondBrain/wiki/projects/llm_configs.md; /Users/sahuno/projects/personal/secondBrain/state/projects.csv
- **Commands that worked:** ledger-append --create --project llm_configs --file /Users/sahuno/projects/llm_configs --who 'Claude (Opus 5), seeding' ... --next-action 'Load at project start; no next feature'
- **Known issues / blockers:** seeded, not verified: correct anything stale; facts here are as of the compile date
- **Exact next steps:** 1. Load at project start; no next feature is queued (state/projects.csv, 2026-08-18).
