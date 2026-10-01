---
project: llm_configs
status: active
owner: Samuel Ahuno
team: Samuel only
next_action: Merge PR #22, then update the three plugins on the Mac
blockers: none
updated: 2026-09-30
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

### 2026-09-30 20:35 · Claude Opus 5.5 · Rebased local work onto the new main and opened PR #22
- **Done:** Committed the plugins-off settings (dea1d67), the cloud-sync transfer note with its SKILL.md row (a63c374) and the ledger (48cedff). The new note's one cluster path is classified EVIDENCE in docs/site-path-allowlist.tsv. Moved all 5 unpushed commits onto a new branch, plugins-off-and-cloud-sync, rebased onto origin/main and resolved 2 conflicts: the allowlist (kept both sides' rows) and PROGRESS.md (both sides' entries kept, newest first). Pushed and opened https://github.com/sahuno/llm_configs/pull/22. The old branch figure-style-consolidation is left as it was; it was already merged in #20.
- **Key paths:** claude/settings.json; plugins/hpc-site/skills/mskcc-hpc/SKILL.md; plugins/hpc-site/skills/mskcc-hpc/references/cloud_sync_destination.md; docs/site-path-allowlist.tsv; PROGRESS.md
- **Commands that worked:** git rebase origin/main; bash tools/audit_site_paths.sh (unreviewed 0); ./plugins/bio-guardrails/tests/test_hooks.sh (42 passed, 0 failed); python3 tools/gotcha_audit.py (all records complete)
- **Known issues / blockers:** CI on PR #22 was not checked at the time of writing. Biology projects on this Mac still need the three plugins turned back on per project.
- **Exact next steps:** 1. Check CI on PR #22 and merge it. 2. On the Mac: git switch main && git pull, then claude plugin marketplace update sahuno and update the three plugins to 1.2.0. 3. Add enabledPlugins true for the three sahuno plugins to .claude/settings.json in each biology project. 4. Optionally delete the merged local branch figure-style-consolidation.

### 2026-09-30 20:28 · Claude Opus 5.5 · Checked GitHub for updates: main is 22 commits ahead, PRs #20 and #21 merged
- **Done:** Ran git fetch only. origin/main gained 22 commits, including PR #20 (this branch) and PR #21 (hpc-plugin-migration: analysis-playbooks skill, HPC-only gotchas ported into plugins, mosdepth-scope-warning hook, plugins bumped to 1.2.0). figure-style-consolidation is 2 commits ahead of its upstream (aeb57e9, 702867a, not pushed) and 9 behind origin/main. The agent edited no files. claude/settings.json was rewritten at 15:28 today by Claude Code itself (added model: opus, moved advisorModel), on top of the 2026-09-27 uncommitted change that turned off the three sahuno plugins.
- **Key paths:** claude/settings.json (uncommitted), PROGRESS.md (uncommitted), plugins/hpc-site/skills/mskcc-hpc/SKILL.md (uncommitted), plugins/hpc-site/skills/mskcc-hpc/references/cloud_sync_destination.md (untracked)
- **Commands that worked:** git fetch --all --prune; git log --oneline main..origin/main; git diff --stat HEAD...origin/main
- **Known issues / blockers:** PROGRESS.md changed both locally and on origin/main, so bringing in main needs a manual merge of that file. The plugins being off globally (2026-09-27) now hides the 1.2.0 updates in non-biology projects, which is intended.
- **Exact next steps:** 1. Commit the local edits. 2. Rebase or merge onto origin/main and resolve PROGRESS.md by hand. 3. Push and open a PR for aeb57e9, 702867a and the new commit. 4. Classify cloud_sync_destination.md as site-specific or general.

### 2026-09-30 17:34 · Claude (Opus 5.5), HPC session · HPC migrated to the sahuno plugins; HPC-only content ported; CLAUDE.md 39.7k -> 25.5k; /wrapup writes the ledger
- **Done:** Merged PR #20 (225bbee). Saved HPC uncommitted work on local branch hpc-local-snapshot-20260930 (4c3506b, not pushed: public repo). On branch hpc-plugin-migration: ported deeptools, liftover_chains, verification_discipline into analysis-gotchas; 3-way merged HPC edits to clair3, igv, mskcc_partitions, snakemake, vllm_iris and containers.yaml; added mosdepth-scope-warning to bio-guardrails with 6 tests (42/42 pass, jq and python3-only); /wrapup, /gates and README now name the PROGRESS.md ledger; CLAUDE.md carries the ledger section and moves the domain playbooks, pipeline conventions, AI engineering, manuscript figures and the full logging spec into a new analysis-playbooks skill (verbatim); plugins bumped to 1.2.0. HPC cutover: ~/projects/llm_configs -> /data1 checkout; sahuno directory marketplace + 3 plugins installed; settings.json keeps only the bell and ledger hooks (ledger-hook on PATH); old skill/command/profile links and ~/.claude/hooks removed; ~/.claude/CLAUDE.md -> repo; SITE_CONFIG resolved in ~/.bashrc.local.
- **Key paths:** claude/CLAUDE.md; plugins/bio-skills/skills/analysis-playbooks/; plugins/bio-skills/skills/analysis-gotchas/; plugins/bio-guardrails/hooks/mosdepth-scope-warning.sh; plugins/bio-guardrails/tests/test_hooks.sh; plugins/bio-skills/commands/wrapup.md; docs/site-path-allowlist.tsv; HPC backups and UNDO: ~/.claude/backups/20260930_llmconfigs_migration/
- **Commands that worked:** claude plugin marketplace add /home/ahunos/projects/llm_configs; claude plugin install bio-skills@sahuno --scope user (same for bio-guardrails, hpc-site); ./plugins/bio-guardrails/tests/test_hooks.sh; ./tools/audit_site_paths.sh; python3 tools/gotcha_audit.py
- **Known issues / blockers:** skillOverrides does not apply to plugin skills in Claude Code 2.1.285 (bare, bio-skills:, @sahuno:, plugin: keys all tried), so cohort-overview, docker-hpc, journal-club, scatter-gather and runtime-resource-study are on again on HPC. house-style test_letter_overlay_does_not_embed_ambient_face fails on HPC only (no Liberation Sans/Helvetica fonts); passes in CI. Mac not reached from the compute node (tunnel on a login node; no key auth to islogin01).
- **Exact next steps:** 1. Review and merge the hpc-plugin-migration PR. 2. On the Mac: git pull main, then claude plugin marketplace update sahuno and update the three plugins. 3. Apply ledger-hook.digest.patch in the singularity repo and reinstall on both hosts. 4. Decide how to hide unused bio-skills skills per host (disable-model-invocation, a separate plugin, or accept). 5. Open item moved from CLAUDE.md: create a database of memory requirements for common workflows or create slurm templates, implement tags like `highCompute_highTime`, `lowTime_lowCompute`. slurm-mcp has snapshot of resource limitations like componc_onc <= 7days

### 2026-09-27 13:56 · Claude Opus 5.5 · Turned off bio-skills, bio-guardrails and hpc-site globally to save start-up context
- **Done:** In claude/settings.json (the file ~/.claude/settings.json links to), enabledPlugins now sets bio-skills@sahuno, bio-guardrails@sahuno and hpc-site@sahuno to false. The bio-skills descriptions alone were 13,007 bytes (~3,200 tokens) loaded in every project, including non-biology ones. JSON validated after the edit.
- **Key paths:** claude/settings.json
- **Commands that worked:** python3 -c "import json;json.load(open('claude/settings.json'))"
- **Known issues / blockers:** Biology projects on this laptop now lack these plugins, including the bio-guardrails safety hooks, until each one sets them back to true in its own .claude/settings.json. Not committed.
- **Exact next steps:** 1. Add {"enabledPlugins": {"bio-skills@sahuno": true, "bio-guardrails@sahuno": true, "hpc-site@sahuno": true}} to .claude/settings.json in each biology project. 2. Commit claude/settings.json.

### 2026-09-25 15:06 · Claude (Opus 5.5) · Committed Vercel disable; deleted use-railway skill
- **Done:** Committed vercel@claude-plugins-official=false as aeb57e9. Deleted the use-railway skill from both places it was installed: ~/.claude/skills/use-railway (the copy Claude Code loads) and ~/.agents/skills/use-railway (the copy other agents read). Neither copy was listed in ~/.agents/.skill-lock.json, so no lock entry needed removing.
- **Key paths:** claude/settings.json (committed aeb57e9); ~/.claude/skills/use-railway and ~/.agents/skills/use-railway (deleted, outside the repo)
- **Commands that worked:** rm -rf ~/.claude/skills/use-railway ~/.agents/skills/use-railway
- **Known issues / blockers:** Takes effect next session. claude.ai connectors (Vercel, Gmail, Hugging Face) have to be turned off in claude.ai settings, not here.
- **Exact next steps:** 1. Start a new session and compare /context against this one. 2. Classify the site path in cloud_sync_destination.md in docs/site-path-allowlist.tsv, then commit it with the mskcc-hpc SKILL.md change.

### 2026-09-25 15:04 · Claude (Opus 5.5) · Committed settings drift; disabled Vercel plugin and removed Railway MCP to shrink startup context
- **Done:** Committed the 3 keys Claude Code had added to claude/settings.json (702867a). The user asked why one message already fills about 6% of the context window. The main cause is fixed text loaded at session start: about 450 on-demand tool names (about 300 from Vercel, about 50 from Railway), about 40 Vercel skill descriptions, tool and connector instructions, CLAUDE.md and the ledger injected by the start-up hook. None of these were measured; /context shows the real split. On request: set vercel@claude-plugins-official to false in claude/settings.json (still uncommitted), and ran claude mcp remove railway, which edited ~/.claude.json; that file is not tracked in this repo.
- **Key paths:** claude/settings.json (enabledPlugins.vercel=false, uncommitted); ~/.claude.json (railway MCP server removed); ~/.claude/skills/use-railway (still installed, not touched)
- **Commands that worked:** jq ".enabledPlugins[\"vercel@claude-plugins-official\"]=false" claude/settings.json > new && jq empty new && cat new > claude/settings.json  # cat, not mv, keeps the symlink target a regular file; claude mcp remove railway
- **Known issues / blockers:** The change takes effect in the next session, not this one. The use-railway skill still loads its description. claude.ai connectors (Gmail, Vercel, Hugging Face) are set on claude.ai, not here.
- **Exact next steps:** 1. Start a new session and compare /context against this one. 2. Commit the vercel=false change in claude/settings.json if it is kept. 3. Optional: remove ~/.claude/skills/use-railway.

### 2026-09-25 14:59 · Claude (Opus 5.5) · Answered: IGV skill exists; settings.json symlink survived a Claude Code settings write
- **Done:** Read-only question answered: the repo has an IGV skill, plugins/bio-skills/skills/igv-screenshots (igver-based, headless IGV in Singularity/Docker). This session changed no files. The stop hook flagged claude/settings.json, but that edit was already present when the session started (mtime Sep 24 18:15). Claude Code wrote it itself through the ~/.claude/settings.json symlink: it added preferredNotifChannel "auto", switchModelsOnFlag true, advisorModel "fable". Checked with ls -la: ~/.claude/settings.json is still a symlink into the repo, so a settings write by Claude Code does not replace the symlink. That resolves the open question from 2026-09-21.
- **Key paths:** plugins/bio-skills/skills/igv-screenshots/ (read only); claude/settings.json (changed by Claude Code, not by this session; uncommitted)
- **Commands that worked:** ls -la ~/.claude/settings.json  # expect -> .../llm_configs/claude/settings.json; git diff claude/settings.json
- **Known issues / blockers:** claude/settings.json has 3 uncommitted keys added by Claude Code; the repo is public, and these keys contain no secrets. cloud_sync_destination.md still has one unreviewed site path (fails tools/audit_site_paths.sh). plugins/hpc-site/skills/mskcc-hpc/SKILL.md still modified and uncommitted.
- **Exact next steps:** 1. Commit the claude/settings.json drift (3 keys) if wanted. 2. Classify the site path in cloud_sync_destination.md in docs/site-path-allowlist.tsv, then commit it with the mskcc-hpc SKILL.md change.

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
