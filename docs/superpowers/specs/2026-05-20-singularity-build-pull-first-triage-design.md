# Design: pull-first triage gate for the `singularity-build` skill

**Date:** 2026-05-20
**Author:** Samuel Ahuno (with Claude)
**Status:** Approved (design); pending implementation plan
**Branch context:** authored on `claude/scientific-auditor-framework-wkKAi`

## Problem

A colleague on a fresh Claude Code install asked it to "build a bioinformatics
container" and Claude's native instinct was sophisticated: it reached for
pre-built images (`apptainer pull` from biocontainers / Galaxy depot) rather
than building from scratch. That raised the question of whether the lab's
custom `/singularity-build` skill is *in the way* of that native sophistication.

Diagnosis: the skill's value is **bimodal**.

- **Easy end** (pull, Tier 0 pre-built binary, Tier 1 conda install): native
  Claude Code is now genuinely competent. Here the skill mostly adds *bias* — it
  frames every request as "build," and its description explicitly says
  *"Do NOT trigger for pulling pre-built images (apptainer pull)."* So it never
  asks the most important question: **should we build at all?**
- **Hard end** (Tier 2 compiled extensions, Tier 3 fakeroot CUDA, the conda
  compiler/sysroot symlink dance, decoding cryptic `CUDA_INCLUDE_DIRS` /
  `gcc failed` / GLIBC build failures on RHEL 8): native Claude almost certainly
  does **not** know this. The knowledge is rare and was captured from real build
  failures on MSKCC HPC. It is irreplaceable.

So "redundant" is true for the top of the funnel and false for the bottom. The
fix is **repositioning**, not retire-vs-keep.

## Decision

Add a **Step 0: Acquire-vs-build triage** ahead of the current
"Step 1: Classify the Build Tier." The skill's goal changes from *"build a
container"* to *"produce a working SIF"* — building from scratch becomes the
**fall-through**, not the default.

The differentiator over native Claude is the **verification step**. Native
Claude pulls and declares victory. On this HPC a pulled image can still be
broken two documented ways:

- **GLIBC 2.28 mismatch** — modern images assume newer glibc (already named as a
  build-environment constraint in the skill).
- **SSL/CA env-leak** — host `SSL_CERT_FILE` / `SSL_CERT_DIR` crash httpx-based
  tools at first network call (see `rules/apptainer_env_leak.md`).

The gate pulls **and verifies against the real RHEL 8 constraints**, and only
when that fails does it drop into the expensive Tier 0→3 build machinery —
carrying the failure reason with it.

### Chosen direction (from brainstorming)

- **Direction:** add a pull-first triage gate (one skill, smallest change).
  Rejected: split into two skills, slim+narrow trigger, retire into `rules/`.
- **Implementation shape:** Approach **B** — prose gate in `SKILL.md` plus one
  helper script `scripts/find_prebuilt.sh`. Verification stays prose (judgment-
  heavy; a rigid pass/fail script would be brittle against novel GLIBC/SSL
  failure text). Rejected: prose-only (A, leaves source-probing freehand);
  prose + verify_pulled.sh (C, risks false confidence on unmatched failures).
- **Trigger wording:** deferred to implementation. The contradictory
  *"Do NOT trigger for pulling pre-built images"* line must be reconciled, but
  exact phrasing (broaden to "get me a container for X" vs. keep build-triggered
  and run the gate internally) is settled when editing `SKILL.md`.

## Triage decision order (the new Step 0)

1. **Lab catalog first** — grep
   `profiles/software_configs/softwares_containers_config.yaml`; never
   re-acquire what is already registered.
2. **Upstream pre-built, in priority order** (lifted from existing lab rules):
   1. **Galaxy depot** — `https://depot.galaxyproject.org/singularity/<tool>:<ver>`.
      Direct SIF, no auth, no rate-limit. `rules/severus.md` already documents
      this as the winning path (quay rate-limits; Seqera/wave needs auth).
   2. **nf-core module** container reference — canonical, version-pinned.
   3. **biocontainers** — `docker://quay.io/biocontainers/<tool>:<tag>`
      (note: anonymous quay `apptainer pull` is rate-limited).
   4. Tool's official **Docker Hub / GHCR / vendor** image.
3. **Pull** — with `APPTAINER_CACHEDIR` set and host bind vars unset (consistent
   with the existing build-script hygiene rules).
4. **Verify on RHEL 8** — run `tool --version` **plus** exercise one real
   code/network path; watch for `GLIBC_2.xx not found` and the SSL-leak crash;
   use `--cleanenv` as the diagnostic split (clean works + non-clean fails ⇒
   env-leak, not a build defect).
5. **Decide:**
   - Verifies clean → register in the containers config, done. No build.
   - No pre-built found, **or** verification fails → fall through to Step 1
     (classify tier) and build from scratch, recording *why* the pull path was
     rejected.

## Components / changes

1. **`SKILL.md`**
   - New **Step 0** section with the decision tree above (renumber existing
     Steps 1–4 to follow, or label Step 0 explicitly ahead of Step 1 — keep
     existing tier content unchanged as the fall-through).
   - Reconcile the description: remove/soften the *"Do NOT trigger for pulling"*
     exclusion (exact wording at implementation time). Keep the genuine
     exclusion for running an existing container (`apptainer exec/run`).
   - Short "When pulling beats building" rationale box cross-referencing
     `rules/severus.md` (Galaxy depot) and `rules/apptainer_env_leak.md`
     (verification).
   - Bump skill `version` (1.0.0 → 1.1.0).
2. **`scripts/find_prebuilt.sh`** (new) — input: tool name + version (+ optional
   platform). Probes, in priority order: lab catalog, Galaxy depot URL
   existence (HTTP HEAD), quay biocontainers tag, official image. Output:
   ranked, ready-to-run `apptainer pull` commands with a one-line note per
   source (auth/rate-limit caveats). Mirrors the existing
   `generate_def.sh` / `generate_build_script.sh` mechanical-helper pattern.
   Must be SLURM-safe and quote/exit cleanly when a source is unreachable.
3. **`references/build_guide.md`** — add the source-priority table and the RHEL 8
   verification checklist (GLIBC scan, `--cleanenv` SSL split, smoke + real-path
   test) so the prose verification step has an authoritative reference.

## Out of scope (YAGNI)

- A `verify_pulled.sh` battery script (Approach C) — verification stays prose.
- Splitting into separate acquire/build skills.
- Docker/Podman build paths (covered by the separate `docker-hpc` skill).
- Changing the Tier 0–3 build recipes themselves — they are untouched.

## Success criteria

- For a tool with a clean Galaxy-depot image (e.g. a samtools-class Tier 1
  tool), the skill produces a verified pulled SIF **without** writing a `.def`
  or invoking a build.
- For a tool with no pre-built image, or one that fails RHEL 8 verification, the
  skill falls through to the existing build tiers with the rejection reason
  recorded.
- `find_prebuilt.sh` returns ranked pull candidates for a known tool and exits
  cleanly (no candidates found) for a tool that genuinely must be built.
- The `SKILL.md` description no longer contradicts itself on pulling.

## Cross-references

- `rules/severus.md` — Galaxy depot is the reliable no-auth/no-rate-limit pull
  source; quay rate-limits, Seqera/wave needs auth.
- `rules/apptainer_env_leak.md` — host SSL/CA env vars crash pulled httpx-based
  tools; `--cleanenv` diagnostic; verify the network path, not just `--help`.
- `rules/apptainer_vs_conda.md` — SIF cold-start advantage (context for
  preferring a registered SIF).
- `docker-hpc` skill — owns Docker/Podman build paths (no overlap).
