# Pull-First Triage Gate for singularity-build — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reposition the `singularity-build` skill so it tries to acquire a verified pre-built image (Galaxy depot → nf-core → biocontainers) before falling through to a from-scratch Tier 0→3 build.

**Architecture:** Add a prose "Step 0: Acquire-vs-build triage" to `SKILL.md`, backed by one mechanical helper `scripts/find_prebuilt.sh` that resolves the exact biocontainers tag and emits ranked `apptainer pull` commands. Verification of a pulled image against RHEL 8 constraints (GLIBC, SSL env-leak) stays prose. Existing Tier 0→3 build content is untouched and becomes the documented fall-through.

**Tech Stack:** Bash (helper + tests, no bats — plain assertion script), Markdown (SKILL.md, build_guide.md), `curl` + `python3` for the quay.io tag API (python3 over jq to avoid a dependency).

**Working directory for all paths below:** `/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/singularity-build`

---

### Task 1: `find_prebuilt.sh` core — args, catalog check, offline templates

**Files:**
- Create: `scripts/find_prebuilt.sh`
- Create: `scripts/test_find_prebuilt.sh`

- [ ] **Step 1: Write the failing test**

Create `scripts/test_find_prebuilt.sh`:

```bash
#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-05-20
# Purpose: Offline tests for find_prebuilt.sh (no network; uses --no-probe).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${HERE}/find_prebuilt.sh"
fail=0

check() { # desc expected_exit actual_exit output needle
  local desc="$1" exp="$2" act="$3" out="$4" needle="$5"
  if [[ "$act" != "$exp" ]]; then echo "FAIL [$desc]: exit $act != $exp"; fail=1; return; fi
  if [[ -n "$needle" ]] && ! grep -qF "$needle" <<<"$out"; then
    echo "FAIL [$desc]: output missing '$needle'"; fail=1; return; fi
  echo "PASS [$desc]"
}

# Case 1: missing --version -> usage, exit 2
out="$("$SCRIPT" --name samtools 2>&1)"; check "missing-version" 2 "$?" "$out" ""

# Case 2: --no-probe prints the Galaxy depot template, exit 0
out="$("$SCRIPT" --name samtools --version 1.21 --no-probe --catalog /dev/null 2>&1)"
check "no-probe-template" 0 "$?" "$out" "depot.galaxyproject.org/singularity/samtools:<TAG>"

# Case 3: catalog hit -> exit 3
tmp="$(mktemp)"; printf 'samtools:\n  sif: /path/samtools_1.21.sif\n' >"$tmp"
out="$("$SCRIPT" --name samtools --version 1.21 --no-probe --catalog "$tmp" 2>&1)"
check "catalog-hit" 3 "$?" "$out" "ALREADY REGISTERED"
rm -f "$tmp"

[[ "$fail" -eq 0 ]] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test_find_prebuilt.sh`
Expected: FAIL — `find_prebuilt.sh` does not exist yet, every case errors (non-zero, "No such file").

- [ ] **Step 3: Write minimal implementation**

Create `scripts/find_prebuilt.sh`:

```bash
#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-05-20
# Purpose: Probe for a pre-built Apptainer/Docker image for a bioinformatics
#          tool BEFORE falling through to a from-scratch build. Implements the
#          source-priority + catalog-first logic of the singularity-build
#          skill's Step 0 (acquire-vs-build triage).
set -euo pipefail

NAME=""; VERSION=""; PROBE=1
CATALOG="${SOFTWARES_CONTAINERS_CONFIG:-/data1/greenbab/users/ahunos/apps/llm_configs/claude/profiles/software_configs/softwares_containers_config.yaml}"

usage() {
  cat <<EOF
Usage: find_prebuilt.sh --name TOOL --version VER [--no-probe] [--catalog FILE]
  --name      tool name as known to bioconda/biocontainers (required)
  --version   version string, e.g. 1.21 (required)
  --no-probe  skip network calls; print candidate templates only (offline/testable)
  --catalog   path to softwares_containers_config.yaml (default: lab config)
Exit codes: 0 candidates printed | 2 usage error | 3 already in catalog | 4 no candidates
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --version) VERSION="$2"; shift 2;;
    --no-probe) PROBE=0; shift;;
    --catalog) CATALOG="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2;;
  esac
done
[[ -z "$NAME" || -z "$VERSION" ]] && { usage; exit 2; }

# 1. Lab catalog first — never re-acquire a registered image
if [[ -f "$CATALOG" ]] && grep -iqE "(^|[^a-z])${NAME}([^a-z]|$)" "$CATALOG"; then
  echo "ALREADY REGISTERED in catalog ($CATALOG):"
  grep -inE "(^|[^a-z])${NAME}([^a-z]|$)" "$CATALOG" || true
  echo ">> Reuse the registered SIF; no pull/build needed."
  exit 3
fi

# 2. (network tag resolution added in Task 2) — placeholder keeps offline path working
TAG=""

# 3. Emit candidates (offline template path; network-resolved path added in Task 2)
echo "=== Pre-built image candidates for ${NAME} ${VERSION} ==="
if [[ -z "$TAG" ]]; then
  echo "(--no-probe) candidate templates (resolve <TAG> = version--buildhash via quay tags):"
  echo "    apptainer pull https://depot.galaxyproject.org/singularity/${NAME}:<TAG>"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:<TAG>"
  exit 0
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `chmod +x scripts/find_prebuilt.sh scripts/test_find_prebuilt.sh && bash scripts/test_find_prebuilt.sh`
Expected: `PASS [missing-version]`, `PASS [no-probe-template]`, `PASS [catalog-hit]`, `ALL PASS` (exit 0).

- [ ] **Step 5: Commit**

```bash
git add scripts/find_prebuilt.sh scripts/test_find_prebuilt.sh
git commit -m "feat(singularity-build): find_prebuilt.sh core — catalog check + offline templates"
```

---

### Task 2: `find_prebuilt.sh` network probe — resolve biocontainers tag, ranked output

**Files:**
- Modify: `scripts/find_prebuilt.sh` (replace the Task-1 `# 2.` placeholder block and the `# 3.` emit block)
- Modify: `scripts/test_find_prebuilt.sh` (add an offline regression that the ranked-output text is present under a forced tag)

- [ ] **Step 1: Write the failing test**

Append before the final summary lines in `scripts/test_find_prebuilt.sh`:

```bash
# Case 4: forced-tag path prints ranked Galaxy-depot-PREFERRED block + verify reminder
out="$(FORCE_TAG=1.21--h50ea8bc_0 "$SCRIPT" --name samtools --version 1.21 --no-probe --catalog /dev/null 2>&1)"
check "ranked-preferred" 0 "$?" "$out" "Galaxy depot (direct SIF"
check "verify-reminder"  0 "$?" "$out" "VERIFY on RHEL 8"
check "glibc-reminder"   0 "$?" "$out" "GLIBC"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test_find_prebuilt.sh`
Expected: the three new cases FAIL — current script ignores `FORCE_TAG` and prints only the `<TAG>` template, so "Galaxy depot (direct SIF" / "VERIFY on RHEL 8" / "GLIBC" are absent.

- [ ] **Step 3: Write minimal implementation**

In `scripts/find_prebuilt.sh`, replace the `# 2.` placeholder block with the resolver (honors `FORCE_TAG` for offline testing, else queries quay):

```bash
# 2. Resolve the exact biocontainers tag (version + build suffix)
TAG="${FORCE_TAG:-}"
if [[ -z "$TAG" && "$PROBE" -eq 1 ]]; then
  API="https://quay.io/api/v1/repository/biocontainers/${NAME}/tag/?onlyActiveTags=true&filter_tag_name=like:${VERSION}"
  TAG="$(curl -sf "$API" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tags = [t["name"] for t in d.get("tags", [])]
tags = [t for t in tags if "--" in t] or tags
print(tags[0] if tags else "")
' 2>/dev/null || true)"
fi
```

Then replace the entire `# 3.` emit block with:

```bash
# 3. Emit ranked candidates
echo "=== Pre-built image candidates for ${NAME} ${VERSION} ==="
if [[ -n "$TAG" ]]; then
  echo "[1] Galaxy depot (direct SIF, no auth, no rate-limit) — PREFERRED:"
  echo "    apptainer pull ${NAME}_${TAG}.sif https://depot.galaxyproject.org/singularity/${NAME}:${TAG}"
  echo "[2] biocontainers via quay (anonymous pull is RATE-LIMITED):"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:${TAG}"
  echo "[3] nf-core module (canonical, version-pinned container line):"
  echo "    https://github.com/nf-core/modules/tree/master/modules/nf-core/${NAME}"
  echo
  echo ">> After pull: VERIFY on RHEL 8 — run '<tool> --version' AND exercise one real path."
  echo ">> Watch for: GLIBC_2.xx-not-found, and SSL_CERT_FILE httpx crashes (use --cleanenv to split env-leak from a real defect)."
  echo ">> If verification fails or no image works, fall through to a build: scripts/generate_def.sh ..."
  exit 0
fi
if [[ "$PROBE" -eq 0 ]]; then
  echo "(--no-probe) candidate templates (resolve <TAG> = version--buildhash via quay tags):"
  echo "    apptainer pull https://depot.galaxyproject.org/singularity/${NAME}:<TAG>"
  echo "    apptainer pull docker://quay.io/biocontainers/${NAME}:<TAG>"
  exit 0
fi
echo "No biocontainers tag matched '${VERSION}'. Check then build:"
echo "  - nf-core module: https://github.com/nf-core/modules/tree/master/modules/nf-core/${NAME}"
echo "  - tool's official Docker Hub / GHCR image"
echo "  - else from-scratch: scripts/generate_def.sh --name ${NAME} --version ${VERSION} --tier <0|1|2|3> ..."
exit 4
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/test_find_prebuilt.sh`
Expected: all cases including `PASS [ranked-preferred]`, `PASS [verify-reminder]`, `PASS [glibc-reminder]`, `ALL PASS` (exit 0).

- [ ] **Step 5: Optional live smoke (network; non-gating)**

Run: `scripts/find_prebuilt.sh --name samtools --version 1.21 || true`
Expected (if quay reachable): a `[1] Galaxy depot ...` block with a resolved tag like `1.21--h50ea8bc_0`. If the network is blocked it exits 4 with the build fall-through hint — both are acceptable; do not gate the commit on this.

- [ ] **Step 6: Commit**

```bash
git add scripts/find_prebuilt.sh scripts/test_find_prebuilt.sh
git commit -m "feat(singularity-build): find_prebuilt.sh resolves quay tag + emits ranked pull candidates"
```

---

### Task 3: Add "Step 0: Acquire-vs-build triage" to SKILL.md

**Files:**
- Modify: `SKILL.md` (insert a new section immediately before the line `## Step 1: Classify the Build Tier`)

- [ ] **Step 1: Insert the Step 0 section**

Using Edit, place the following block immediately before `## Step 1: Classify the Build Tier` in `SKILL.md`:

```markdown
## Step 0: Acquire-vs-build triage (do this FIRST)

The goal is a **working SIF**, not necessarily a *built* one. Building from
scratch is the fall-through, not the default. Before classifying a build tier,
try to acquire a verified pre-built image.

**Run the helper to get ranked candidates:**

```bash
scripts/find_prebuilt.sh --name <tool> --version <ver>
```

It checks the lab catalog first (exit 3 = already registered, reuse it), then
resolves the exact biocontainers tag and prints ranked `apptainer pull`
commands. Source priority (hard-won — see `rules/severus.md`):

1. **Galaxy depot** `https://depot.galaxyproject.org/singularity/<tool>:<tag>` —
   direct SIF, no auth, no rate-limit. **Preferred.**
2. **nf-core module** container reference — canonical, version-pinned.
3. **biocontainers** `docker://quay.io/biocontainers/<tool>:<tag>` — works, but
   anonymous quay pulls are rate-limited.
4. Tool's official Docker Hub / GHCR / vendor image.

**Then VERIFY the pulled image on RHEL 8 — this is the step that makes pulling
safe here, and the reason this skill still owns the easy path:**

- Run `<tool> --version` **and** exercise one real code/network path (not just
  `--help` — see `rules/apptainer_env_leak.md`).
- A pull can still be broken two ways on this HPC:
  - **GLIBC 2.28 mismatch** — `version 'GLIBC_2.xx' not found`. The image
    assumes a newer glibc than RHEL 8 provides.
  - **SSL/CA env-leak** — host `SSL_CERT_FILE`/`SSL_CERT_DIR` crash httpx-based
    tools at first network call. Diagnose with `--cleanenv`: if
    `apptainer exec --cleanenv` works where plain `exec` fails, it is an
    env-leak, not a build defect.

**Decide:**
- Verifies clean → register in
  `profiles/software_configs/softwares_containers_config.yaml`, done. **No build.**
- No pre-built image, or verification fails → fall through to Step 1, building
  from scratch and recording *why* the pull path was rejected.

```

- [ ] **Step 2: Verify the section is present and well-formed**

Run: `grep -n "Step 0: Acquire-vs-build triage" SKILL.md && grep -n "Step 1: Classify the Build Tier" SKILL.md`
Expected: Step 0 line number is smaller than the Step 1 line number (Step 0 precedes Step 1).

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(singularity-build): add Step 0 acquire-vs-build triage gate"
```

---

### Task 4: Reconcile the skill description + version bump

**Files:**
- Modify: `SKILL.md` (front-matter `description` and `version`)

- [ ] **Step 1: Remove the self-contradictory pull exclusion**

The current front-matter ends the description with:

```
  Do NOT trigger for: running an existing container (apptainer exec/run),
  pulling pre-built images (apptainer pull), or Docker/Podman workflows.
```

Using Edit, replace those two lines with:

```
  Once triggered, the skill triages pull-vs-build (Step 0): it tries to acquire
  and verify a pre-built image before building from scratch.
  Do NOT trigger for: running an existing container (apptainer exec/run) or
  Docker/Podman build workflows (use the docker-hpc skill for those).
```

- [ ] **Step 2: Bump the version**

Using Edit, change `version: 1.0.0` to `version: 1.1.0` in the front-matter.

- [ ] **Step 3: Verify no remaining contradiction**

Run: `grep -n "pulling pre-built images" SKILL.md; grep -n "^version:" SKILL.md`
Expected: the first grep prints **nothing** (the exclusion is gone); the second prints `version: 1.1.0`.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "docs(singularity-build): reconcile trigger with pull-first gate; bump to 1.1.0"
```

---

### Task 5: Source-priority table + RHEL 8 verification checklist in build_guide.md

**Files:**
- Modify: `references/build_guide.md` (append a new section at end of file)

- [ ] **Step 1: Append the reference section**

Append the following to the end of `references/build_guide.md`:

```markdown

## Acquire-vs-build: source priority and RHEL 8 verification

Step 0 of the skill tries to pull a verified pre-built image before building.
Use `scripts/find_prebuilt.sh --name <tool> --version <ver>` to generate ranked
candidates. Reference detail below.

### Source priority

| Rank | Source | Pull form | Caveat |
|------|--------|-----------|--------|
| 1 | Galaxy depot | `apptainer pull https://depot.galaxyproject.org/singularity/<tool>:<tag>` | Direct SIF, no auth, no rate-limit. Preferred. |
| 2 | nf-core module | container line in `modules/nf-core/<tool>/main.nf` | Canonical, version-pinned. |
| 3 | biocontainers (quay) | `apptainer pull docker://quay.io/biocontainers/<tool>:<tag>` | Anonymous quay pulls are rate-limited. |
| 4 | Official image | `apptainer pull docker://<vendor>/<tool>:<tag>` | Quality/maintenance varies; verify carefully. |

The `<tag>` is `version--buildhash` (e.g. `1.21--h50ea8bc_0`). Resolve it from
the quay tags API (what `find_prebuilt.sh` does):
`https://quay.io/api/v1/repository/biocontainers/<tool>/tag/?onlyActiveTags=true&filter_tag_name=like:<version>`.

### RHEL 8 verification checklist (run after every pull, before trusting a SIF)

- [ ] `apptainer exec <sif> <tool> --version` succeeds.
- [ ] Exercise one **real** path (a tiny conversion, an index, a network call) —
      not just `--help`. httpx-based tools crash only at first client init.
- [ ] No `version 'GLIBC_2.xx' not found` — if present, the image needs newer
      glibc than RHEL 8 (2.28) has → build from scratch instead.
- [ ] `--cleanenv` diagnostic: if `apptainer exec --cleanenv <sif> <cmd>`
      succeeds where plain `exec` fails, it is the host SSL/CA env-leak
      (`SSL_CERT_FILE`/`SSL_CERT_DIR`), not a build defect. See
      `rules/apptainer_env_leak.md`.
- [ ] On clean verification: register the SIF in
      `profiles/software_configs/softwares_containers_config.yaml`.
```

- [ ] **Step 2: Verify the section landed**

Run: `grep -n "Acquire-vs-build: source priority" references/build_guide.md && grep -c "GLIBC" references/build_guide.md`
Expected: the heading is found; `GLIBC` count is ≥ 1.

- [ ] **Step 3: Commit**

```bash
git add references/build_guide.md
git commit -m "docs(singularity-build): source-priority table + RHEL8 verification checklist"
```

---

### Task 6: Final self-review against the spec

**Files:**
- Read-only: `SKILL.md`, `scripts/find_prebuilt.sh`, `references/build_guide.md`, the design spec.

- [ ] **Step 1: Re-run the helper test suite**

Run: `bash scripts/test_find_prebuilt.sh`
Expected: `ALL PASS` (exit 0).

- [ ] **Step 2: Confirm each spec success-criterion has a home**

Check by reading, confirm all true:
- Step 0 precedes Step 1 in `SKILL.md` and instructs pull-first + verify + fall-through. (Task 3)
- `find_prebuilt.sh` returns ranked candidates and exits cleanly (3 catalog / 0 found / 4 none). (Tasks 1–2)
- Description no longer says "pulling pre-built images" in the DO-NOT list. (Task 4)
- Source priority + verification reference exists. (Task 5)

Run: `grep -n "pulling pre-built images" SKILL.md` → expected: no output.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A scripts SKILL.md references
git commit -m "chore(singularity-build): final review fixes for pull-first triage" || echo "nothing to commit"
```

---

## Self-Review (plan author)

- **Spec coverage:** Step 0 gate (Task 3), source priority incl. Galaxy-depot-first (Tasks 2,3,5), RHEL 8 verification incl. GLIBC + SSL env-leak (Tasks 3,5), helper script matching the generate_*.sh pattern (Tasks 1–2), description reconciliation + version bump (Task 4), build_guide reference (Task 5), success criteria (Task 6). Out-of-scope items (verify_pulled.sh, skill split, Docker paths, touching Tier recipes) are not implemented — correct. Trigger-breadth was deferred in the spec; Task 4 applies the minimal coherent reconciliation and leaves further broadening optional.
- **Placeholder scan:** No TBD/TODO. All code blocks complete. The `<tool>`/`<ver>`/`<tag>` tokens are intentional CLI placeholders shown to the user, not plan gaps.
- **Type/name consistency:** Helper flags (`--name`, `--version`, `--no-probe`, `--catalog`), env hooks (`FORCE_TAG`, `SOFTWARES_CONTAINERS_CONFIG`), and exit codes (0/2/3/4) are identical across Tasks 1, 2, and the tests. The `FORCE_TAG` test hook introduced in Task 2's test is implemented in Task 2's resolver.
