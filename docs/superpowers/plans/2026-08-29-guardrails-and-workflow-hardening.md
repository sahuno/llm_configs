# Guardrails and Workflow Hardening — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Every task ends with a **Verify** block — a command whose output decides pass/fail. Do not check a box without running it.

**Goal:** Close the correctness gaps found in the plugin restructure, resolve the instruction contradictions in `CLAUDE.md` that actively mislead the model, and convert the inert prose in `prompts/PROMPTS.md` and `CLAUDE.md` §10/§4 into invokable commands.

**Origin:** Findings from the plugin restructure (branch `plugin-restructure`), a `gstack` comparison, and a Fable 5 review pass on 2026-08-29. Where the review was wrong, that is recorded below — its top finding was incorrect and the verification turned up a worse bug in the same file.

**Working directory for all paths:** `/Users/sahuno/projects/llm_configs`

**Standing verification command** (must stay green after every task):

```bash
./plugins/bio-guardrails/tests/test_hooks.sh          # 25 cases, both JSON backends
claude plugin validate . && for p in bio-skills bio-guardrails hpc-site; do
  claude plugin validate "plugins/$p"; done
```

---

## Phase 0 — Done 2026-08-29 (recorded for provenance)

- [x] **Genome-build delimiter bug.** `extract_builds()` in `validate-reference-genome.sh` required `(/|_|^)` before a build name, excluding `.` — the exact delimiter the mandated convention uses (`{sample}.{build}.{description}.{ext}`, CLAUDE.md §2). Consequence: `samtools merge o.bam s.hg38.bam s.mm10.bam` — merging human with mouse — **passed silently**. The two hooks disagreed: `enforce-genome-tag.sh` matched tags with a bare `grep -qiE "($VALID_TAGS)"` and so mandated a format `validate-reference-genome.sh` structurally could not see. Fixed by adding `\.` to the leading class.
- [x] **liftOver exemption.** Fixing the delimiter would have blocked the liftOver workflow CLAUDE.md §2 mandates, and would then block every later command touching the mandated `{sample}.mm39_to_mm10.lifted.bed` filename. Added `is_intentional_conversion()` — matches `liftover|crossmap|.chain|_to_|ALLOW_BUILD_MIX=1`, applies to **same-species only**. Cross-species remains an unconditional block. The old error message promised "re-run with explicit confirmation" with no mechanism behind it; `ALLOW_BUILD_MIX=1` now exists.
- [x] **jq silent-failure.** All 9 hooks began with `jq -r ...`; without jq they returned empty fields, hit the `[ -z "$X" ] && exit 0` early-out, and passed everything through with no message — as `docs/FAQ.md:88` admitted. Added `hooks/lib/json.sh` (`json_get`, `json_backend_check`): prefers jq, falls back to python3, and prints a loud warning when neither exists. 8 safety hooks converted.
- [x] **Test harness.** `plugins/bio-guardrails/tests/test_hooks.sh`, 25 cases. Passes with jq present and with jq removed from `PATH`.

**Not done in Phase 0:** `log-slurm-submission.sh` still uses 10 jq calls including array interpolation. It is a PostToolUse logger, not a guardrail, so silent failure there is tolerable. See Task 5.3.

---

## Phase 1 — Correctness, before this branch is committed

### Task 1.1: CHECK 3 validates stale file content — DONE 2026-08-29 (`ed2e7aa`)

**Confirmed a real bug**, and worse than the review described. CHECK 3 read the YAML from disk, so it judged the wrong state in both directions: a fresh `Write` of a mixed-build config saw no file and returned 0; an `Edit` introducing a second build saw pre-edit content and returned 0. It blocked only when the file was *already* mixed on disk — after the damage.

- [x] Confirmed by test before changing anything.
- [x] `Write` now validates `tool_input.content`; `Edit` reconstructs post-edit text via `old_string` → `new_string`.
- [x] Edit path falls back to `new_string` alone when python3 is unavailable — under-detects rather than over-detects, deliberately, because this hook blocks. A removal-case test guards against false positives.
- [x] `database|reference|genomes` exemption preserved and covered by a test.

Suite is 30 cases, green on both JSON backends.

### Task 1.2: Scrub identifiers — DONE 2026-08-29

**Problem.** `hpc-site` is published as a worked example. `docs/FAQ.md:394` contains a real LDAP UID (not repeated here — see the line). Internal project names (`triplicates_epigenetics_diyva`, `/data1/collab001`) appear throughout. None are secrets; all are avoidable.

**Files:** `claude/docs/FAQ.md`, `README.md`, `plugins/hpc-site/**`

- [x] **Step 1:** Replace the literal UID with a placeholder (`<your-uid>`) and keep the explanation — the LDAP/SSSD/`getpwuid()` mechanism is the valuable part, not the number.
- [x] **Step 2:** Decide per-name whether internal project paths stay. Bind-mount examples in the `sclaude` function need *a* path; a generic one teaches the same thing.

**Verify:**
```bash
# substitute the actual UID from docs/FAQ.md:394
grep -rn "$(sed -n '394p' claude/docs/FAQ.md | grep -oE '[0-9]{9}')" --exclude-dir=.git . && echo "STILL PRESENT" || echo "clean"
```

---

## Phase 2 — Instruction contradictions in CLAUDE.md

Every item here is read by the model each session and acted on. All are sub-hour edits. Verification is manual reading, so each has an explicit acceptance question.

### Task 2.1: Figure font contradiction — DONE (#5)

`CLAUDE.md:442` and `:473` demand "20pt at final size" for Nature figures. `plugins/bio-skills/agents/figure-editor.md:10` states Nature's actual guidance: lettering ~2 mm at final size, 5–8 pt. Both cannot be followed; 20 pt on an 89 mm column is enormous.

- [x] Resolve in favour of the agent for **final** figures. State explicitly that the 20 pt figure applies to on-screen/draft figures before reduction, if that was the intent.
- [x] Make `figure-editor` the named authority for manuscript figures in §7.

**Accept when:** §7 and `figure-editor.md` can both be followed on the same figure without conflict.

### Task 2.2: Multiple-testing default — DONE (#5)

`CLAUDE.md:484` sets `Multiple testing correction | Bonferroni` as a blanket default, while §3C:288 uses DESeq2's `padj < 0.05` — Benjamini–Hochberg. Bonferroni as a genomics discovery default reports ~0 DMRs/DEGs at realistic n.

- [x] Change the default to BH/FDR; reserve Bonferroni for confirmatory tests with small m, and say which is which.
- [x] This becomes load-bearing once the stats-reviewer role (Task 4.2) exists — it will enforce whatever this table says.

**Accept when:** §8 and §3C agree, and the table names when each correction applies.

### Task 2.3: Broken §1 and its FAQ echo — DONE (#5)

- [x] `CLAUDE.md` §1 steps run `1., 2., … 6.` — steps 3–5 were deleted. Renumber.
- [x] Lines 34–36 wedge three unrelated rules (including a `nexflow` typo) between step 2 and its directory tree. Move to §2/§4.
- [x] `docs/FAQ.md:127–133` still documents the deleted 6-step protocol, including "search `~/memories/`" and "read the project file from `~/projects/`". Either restore the resume-from-project-file step in §1 — it is the most valuable of the deleted ones and Task 4.5 depends on it — or correct the FAQ.

**Accept when:** `sed -n '/## 1\./,/^---/p' claude/CLAUDE.md | grep -E '^[0-9]+\.'` is gap-free, and the FAQ describes the steps that exist.

### Task 2.4: Claims — DONE (#5)

- [x] `CLAUDE.md:441` cites a hook `ensure_results_figures.sh` that exists only as a proposal in `claude/inDevelopment/hooks_implementation.md`. The model will assume figure dirs appear automatically and skip creating them. Either implement it (~10 lines, genuinely useful) or delete the claim.
- [x] §6 "Compute Awareness" says "use these as starting estimates" and is followed by no table. Fill it or cut the sentence.

**Verify:**
```bash
grep -n 'ensure_results_figures' claude/CLAUDE.md plugins/bio-guardrails/hooks/*.sh
# must either appear in both, or in neither
```

---

## Phase 3 — Structural

### Task 3.1: Move session classification into the project — DONE 2026-08-29

**Problem.** §1's "ask the user to classify every new conversation" burns the first turn, decays under a strong opening prompt, and re-derives what the working directory already knows. It is the weakest pattern in the file.

**Fix.** Have `init_project.py` write a **project-level `CLAUDE.md`** into the scaffold: domain, genome build, sample-sheet path, aims, status, and a pointer to `~/projects/<slug>.md`. Claude Code auto-loads project CLAUDE.md, so the session self-classifies with no interrogation, and domain becomes a property of the directory.

**Files:** `plugins/bio-skills/scripts/init_project.py`, `claude/CLAUDE.md`, optionally a SessionStart hook

- [x] **Step 1:** Add project-CLAUDE.md generation to `init_project.py`.
- [x] **Step 2:** Shrink §1 to: if no project CLAUDE.md exists, offer `/init-bio-project`.
- [x] **Step 3:** SessionStart hook implemented as `suggest-project-init.sh`. The draft fired on every `UserPromptSubmit` and warned whenever markers were absent, which nags in every non-project directory; this fires once per session and only with positive evidence the directory *is* a project lacking a `CLAUDE.md`.

**Verify:**
```bash
cd $(mktemp -d) && python3 <repo>/plugins/bio-skills/scripts/init_project.py --type analysis --genome hg38
test -f CLAUDE.md && head -20 CLAUDE.md
```

### Task 3.2: The path registry — DONE 2026-08-29

Implemented as **two-axis profiles** rather than a flat `paths.yaml`, on the
author's proposal that profiles give drop-in replacement. The file inventory
showed the existing `profiles/` was mixing two things that compose differently:

- **`sites/`** — cluster facts (genomes, containers, partitions, bind mounts).
  Change when you change institution.
- **`users/`** — person facts (plot defaults, sample-sheet conventions,
  `DO_NOT`). Follow you across institutions. The `.Rprofile` already did
  macOS/Linux/Windows font detection: it was written to travel.

Keeping them on one axis would mean moving institution forces you to rebuild
your plot defaults, and a labmate adopting your site profile inherits your
personal conventions. Adding a cluster is now adding a profile, **not forking
the plugin** — which serves the shareability goal better than the previous
"fork hpc-site" story.

- [x] `profiles/{sites,users}/<name>/`, with `example/` templates on both axes.
- [x] `profiles/resolve.sh`: `SITE_PROFILE`/`USER_PROFILE` select by name,
      `profiles_export` sets the resolved `$SITE_CONFIG`/`$USER_CONFIG`.
      Auto-selects when exactly one real profile exists (templates ignored);
      `USER_PROFILE` falls back to `$USER`; ambiguity **fails and lists
      candidates** rather than guessing.
- [x] `sites/mskcc-greenbaum/paths.yaml` populated from the audit's EXECUTABLE
      set — roots, `APPTAINER_CACHEDIR`, image dir, igver checkout, bind mounts.
- [x] Missing key or file fails loudly naming what to add; never a literal
      fallback. 10-case suite in `profiles/test_resolve.sh`, wired into CI.
- [x] All `$SITE_CONFIG` references repointed; every one verified to resolve.
- [x] `find_prebuilt.sh` catalog default was an absolute `/data1` literal that
      existed on one machine, so its catalog-first check silently never fired
      elsewhere. Now `$SOFTWARES_CONTAINERS_CONFIG` → `$SITE_CONFIG/containers.yaml`.

**Also found and removed:** `profiles/bash_profiles/bashrc_iris_link`, a tracked
symlink to `/home/ahunos/.bashrc` — a file never in the repo, so it had been
dangling for every other user since it was committed.

**Also corrected:** CLAUDE.md claimed Nextflow profiles live in
`$SITE_CONFIG/nextflow/`. No such directory has ever been tracked. Same class as
the Task 2.4 phantom-hook claim.

### Task 3.3: `/data1` triage — DONE 2026-08-29 (all 181 classified, 0 unconverted)

**Problem.** 195 site-path occurrences across `plugins/`. They are three different things that look identical to grep:

| Class | Meaning | Action |
|---|---|---|
| **REGISTRY** | Lives in `hpc-site/profiles/`. That directory *is* the site layer — real paths are its purpose. Swapping these files out is how another cluster is onboarded. | Keep. Auto-classified (100 occurrences). |
| **EVIDENCE** | A citation backing a dated claim. Nobody executes it. e.g. `clair3.md`: "Confirmed 2026-05-05 on Clair3 v2.0.1 GPU SIF (`/data1/.../clair3_v2.0.1_gpu.sif`)". Rewriting it destroys the ability to re-check the finding and turns a falsifiable record into folklore. | Keep, and banner the file as site-measured. |
| **EXECUTABLE** | Gets run or pasted into a command. Broken for everyone else. e.g. `generate_build_script.sh:122` `export APPTAINER_CACHEDIR=/data1/...`. | Convert to resolve from the path registry. |

**The hard cases are intra-file, sometimes intra-bullet.** `analysis-gotchas/references/clair3.md:19` cites an empty `/opt/models` in a specific SIF (evidence) and then says "Extract to `/data1/.../clairs_models/`" (instruction) one sentence apart. A file-level or directory-level grep cannot make this call — which is why the original verify step for this task (`grep -rIl ... | grep -vE '/(evals|examples|references)/'`) was wrong: it excluded `references/` wholesale and would have passed while that embedded instruction stayed broken.

**Mechanism.** `tools/audit_site_paths.sh` enumerates every occurrence line by line and requires each to be classified in `docs/site-path-allowlist.tsv`. Entries are keyed by **file + content hash**, so moving a line is fine but editing it forces re-review — correct, because a changed claim is a new claim. (Hash alone is insufficient: `export APPTAINER_CACHEDIR=...` appears verbatim in 4 files.)

- [x] **Step 1:** `tools/audit_site_paths.sh --bootstrap` — seeds 95 occurrences as `UNREVIEWED` (the 100 registry ones are excluded automatically).
- [x] **Step 2:** Classify all 95 as `EVIDENCE` or `EXECUTABLE`.
- [x] **Step 3:** Convert every `EXECUTABLE` line to resolve from the path registry. Note that identical lines recur across files — the `APPTAINER_CACHEDIR` line needs 4 edits, in `config_template.md`, `build_guide.md`, `generate_build_script.sh`, and `singularity-build/SKILL.md`.
- [x] **Step 4:** Add a "measured on MSKCC HPC; paths are evidence" banner to files with `EVIDENCE` lines.

**Verify:**
```bash
tools/audit_site_paths.sh    # exit 0 only when unreviewed = 0 AND executable-unconverted = 0
```

**Depends on** the path registry design (see note under Task 3.2).

### Task 3.4: Fix the marketplace description — DONE 2026-08-29

`bio-skills` is described in `.claude-plugin/marketplace.json` as purely genomics and never mentions `journal-club`, `docker-hpc`, `runtime-resource-study`, or `scatter-gather` — so the domain-neutral half is invisible to the audience it would serve.

- [x] Rewrite the description to lead with what is domain-neutral, then the genomics specialisation.

---

## Phase 4 — New verbs (the gstack lesson)

The material for all of these already exists as prose. `prompts/PROMPTS.md` is referenced by **zero** files.

### Task 4.1: `/review` — DONE 2026-08-29
- [x] Port the 7-category "Bioinformatics Code Review" from `claude/prompts/PROMPTS.md` (data integrity, genome safety, pipeline correctness, statistical rigor, ONT, reproducibility, forbidden patterns) into `plugins/bio-skills/commands/review.md`, keeping the severity levels and report table.

### Task 4.2: Adversarial reviewer roles — DONE 2026-08-29
- [x] `reviewer-2` — attack the claim before submission (ammunition: `analysis-gotchas/references/numerical_claims.md`).
- [x] `stats-reviewer` — test appropriateness, n, multiple testing (depends on Task 2.2).
- [x] `repro-auditor` — could a stranger rerun this from the repo alone.
- [x] Consider routing one through the installed Codex plugin for a genuinely independent second model.

### Task 4.3: `/verify-run` — DONE 2026-08-29 (script + 13 tests)
The single highest-leverage command here, and it has no gstack analogue. Everything it needs is already specified: `analysis-gotchas`' rule (`sacct` state, `grep -c 'oom_kill events'`), the DSS row-count parity check, and CLAUDE.md's logging spec (`=== DONE ===` marker, before/after filter counts).

- [x] Write `plugins/bio-skills/scripts/verify_run.py` taking a job ID or log path, emitting pass/fail per check.
- [x] Wrap in `commands/verify-run.md`.

**Verify:** run against a known-good log and a known-OOM log; must disagree between them.

### Task 4.4: `/gates` and `/preflight` — DONE 2026-08-29
- [x] `/gates` — CLAUDE.md §10's manual pre-completion checklist, run before declaring anything done.
- [x] `/preflight` — §4's "search nf-core/modules before scaffolding" rule, which already documents what skipping it cost on 2026-05-01.

### Task 4.5: `/wrapup` — DONE 2026-08-29
The README's protected `CLAUDE: DONOT DELETE` block explicitly requests "Logging of tasks completed and pending; logging of daily tasks done". §1's "Project File Content Requirements" already defines the 5-field schema.

- [x] Append that schema to `~/projects/<slug>.md` at session end (command, or SessionEnd hook).
- [x] Depends on Task 2.3 restoring the resume step.

### Task 4.6: `/promote-raw` and the figure manifest — DONE 2026-08-29
- [x] `/promote-raw` — move `data/inbox/` → `data/raw/` with md5sums, a provenance README recording origin, and `chmod -w`. The immutability rule has a blocking hook but no record of what raw *is* or where it came from.
- [x] Figure manifest — §9.5 asks for "a figure index per script". Append `figure_path, script, git_commit, inputs, date` to `results/<run>/figure_index.tsv`; makes manuscript assembly mechanical.

---

## Phase 5 — Knowledge capture at scale

**Principle to adopt:** *a gotcha without a detection command is an opinion.* `references/dss.md` already ends with a verification recipe — make that mandatory.

### Task 5.1: Gotcha frontmatter schema — DONE 2026-08-29
Nearly every entry is version-bound ("modkit 0.6.1", "Snakemake 9", RHEL 8 GLIBC 2.28). Without metadata this becomes folklore.

- [x] Add per-entry frontmatter: `tool`, `version_observed`, `date`, `status: active|fixed-upstream|superseded`, `detect_cmd`.
- [x] Backfill the 15 existing entries.

### Task 5.2: `/add-gotcha` and `/gotcha-audit` — DONE 2026-08-29
- [x] `/add-gotcha` must write **three places**: the reference file, the owning SKILL.md routing table, and the frontmatter. Capture friction is why `rules/` were manual file drops. It should draft from the current session transcript — the moment of failure is when details are cheapest.
- [x] `/gotcha-audit` lists entries whose tool has since changed major version.
- [x] Keep skill *descriptions* categorical ("silent failure modes; consult before trusting any long job that exited 0"), not tool enumerations — the enumeration is the trigger mechanism and will not scale past ~50 entries. At that point split by category (parallel-R, callers, file-format, statistics).

### Task 5.3: Finish `log-slurm-submission.sh` — DONE 2026-08-29
- [x] Convert its 10 jq calls, including the `.jobs[]?` array interpolation, to the `json_get` helper or a python3 block.

---

## Phase 6 — Hygiene — DONE 2026-08-29

- [x] **`save-llm-response` exists in three places** — `claude/prompts/save-{last,response}.md`, untracked `claude/commands/` + `claude/scripts/save_llm_response.py`, and untracked `cli_coding_agents_setups/save-llm-response/` with a *diverging* copy — while `docs/FAQ.md:92` declares the feature superseded by the builtin `/copy`. Keep only the `cli_coding_agents_setups` copy (its stated purpose is non-Claude agents); delete the rest.
- [x] **`examples/examples.md` and `claude/examples/examples.md` are byte-identical**, and their content uses a deprecated container invocation superseded by `sclaude`. Delete one or both.
- [x] **`claude/inDevelopment/CLAUDE.md.dev`** is a stale near-fork of the live file (already missing §0) that will silently drift.
- [x] **`claude/hooks/hooks.yaml`** is self-described dead, wired to nothing, and references a path that does not exist.
- [x] **`claude/skills/` stragglers** — the `igv-reports` moved-out stub, `paper-digest/`, `ideas/`, and the snakemake brainstorm remain in a directory the README says was fully migrated.
- [x] **FAQ restructure pass** — lines 34–44 and 113–123 still teach the pre-plugin `cp` sync workflow and `~/.claude/hooks/` paths, contradicting the install story the README now tells.
- [x] **Move the README's protected FEATURE REQUEST block to GitHub issues.** It is a backlog buried in a README behind a plea not to delete it. (Its UV item is a one-line §4 edit; the Nextflow transition is real work.)

---

## Explicitly deferred, with reasons

- **`research-core` / `genomics` re-split.** Rejected for now. Skills are trigger-gated, so `journal-club` living inside `bio-skills` costs a genomics user nothing. The split churns 100+ renames for taxonomy immediately after a 211-file restructure that is not yet committed. The real problem is the marketplace *description* (Task 3.4). Revisit by extracting a `scholarship` plugin — `journal-club` + `paper-digest` + the literature-review and hypothesis prompts + `figure-editor` + §9.5's publication philosophy — when there is a real external consumer. That is the one plugin here with appeal beyond genomics.
- **Uniform `/data1` scrub.** Replaced by the triage in Task 3.3.
- **A `Writing` domain playbook.** CLAUDE.md has none, though the assets exist. Fold into the `scholarship` extraction rather than writing a fifth playbook now.
- **Growing §5 AI Engineering.** It is 16 lines of generic advice ("use MLflow") while the real AI-eng knowledge sits in `mskcc-hpc/references/vllm_iris.md` and `claude/mcps/mcps.md`. Either grow it from incidents as the bio side grew, or delete it — generic filler in an always-loaded memory file is negative value.

---

## Correction to the record

The Fable 5 review's top-ranked finding claimed `validate-reference-genome.sh` **over-blocks**: that every `liftOver` was refused and the mandated `_to_` filename tripped the hook permanently. Both cases were tested and returned exit 0 — not blocked. The failure ran the opposite way (under-detection, Phase 0). The review pointed at the right file for the wrong reason. Its remaining findings held up on the five that were checked: the jq dependency, the LDAP UID, the §1 numbering gap, the figure-font contradiction, and the Bonferroni/BH contradiction.


---

## Status 2026-08-29: all six phases complete

Shipped across PRs #3–#12. Ten CI jobs gate the repo, each one added because
something here had already failed that way silently:

| Job | Guards against |
|---|---|
| hooks (jq) / hooks (python3-only) | A guardrail that stops guarding when jq is absent |
| SKILL.md casing | A skill invisible on Linux but working on macOS |
| profile resolution | A path that resolves to a guess instead of failing |
| site-path triage | An unclassified site path, or an unconverted literal |
| project scaffolder | A project that cannot self-identify |
| run verification | A run that exits 0 having dropped work |
| gotcha records | An incident record with no version or detector |
| figure manifest | A figure that cannot be traced to its code |
| plugin manifests | A manifest that fails at install time |

Not done, deliberately: the `research-core`/`genomics` split (rejected — skills
are trigger-gated, so it buys taxonomy not function; revisit by extracting a
`scholarship` plugin when there is an external consumer), and growing §5 AI
Engineering, which should grow from incidents or be deleted rather than padded.
