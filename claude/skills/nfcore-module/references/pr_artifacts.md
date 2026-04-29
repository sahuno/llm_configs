# PR Artifacts Templates

## 1. PR Description Template

```markdown
## Summary

- Adds `PROCESS_NAME` process for TOOL_DESCRIPTION
- TYPE_SPECIFIC_BULLET (e.g. "Supports GPU-accelerated X", "Optional Y input", "3 smoothing methods")
- CONTAINER_NOTE (e.g. "Uses official nanoporetech/dorado Docker Hub image — same pattern as parabricks")

## Key design decisions

**[Only include sections relevant to non-standard choices]**

**Container — no bioconda/BioContainers (LICENCE licence)**
TOOL is not on bioconda due to its LICENCE licence. The module uses the official
`ORG/TOOL:TAG` Docker Hub image directly, the same pattern used by parabricks modules
(`nvcr.io/nvidia/...`). `conda null` is set with a comment.
UPSTREAM_TAG_NOTE (e.g. "ONT does not publish semver Docker tags yet — tracked in ISSUE_URL")

**GPU label — `process_gpu`**  [Only for Type C]
The module requires a CUDA GPU and uses `label 'process_gpu'`. This label is defined
in `nf-core/configs` but is flagged as non-standard by lint.

**CI tests — stub only (GPU not available on GitHub Actions)**  [Only for Type C]
- N stub tests run in CI: DESCRIPTION
- N real GPU tests tagged `gpu` are excluded from CI but pass locally
- Precedent: parabricks modules also skip GPU CI tests

## Test data
- `tests/data/TEST_FILE` — DESCRIPTION

## Lint results
- N tests passed, 0 failures, N warnings (EXPLAIN_WARNINGS)

## PR checklist

- [x] This comment contains a description of changes (with reason)
- [x] Added tests
- [x] Followed module conventions
- [x] Test data included
- [x] No TODO statements
- [x] Version broadcast via `topic: versions` / `versions.yml`
- [x] Naming conventions followed (`PROCESS_NAME`)
- [x] Resource label present (`process_LABEL`)
- [x] `conda null` — bioconda not possible (LICENCE), documented  [Type B/C only]
- [ ] `nf-core modules test TOOL/SUBTOOL --profile docker` — PENDING_NOTE
- [ ] `nf-core modules test TOOL/SUBTOOL --profile singularity` — PENDING_NOTE

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 2. Slack #new-modules Draft Template

Use when: Type B (licensed), Type C (GPU), or any non-standard container/label decision.

```
Hi everyone! I'm submitting a new module `TOOL/SUBTOOL` and have
[N question(s)] before I open the PR:

**1. Container — no bioconda/BioContainers (LICENCE licence)**

TOOL is not on bioconda because of its LICENCE licence. I'm using the
official `ORG/TOOL:TAG` Docker Hub image directly:

    container "ORG/TOOL:TAG"

This is the same pattern used by the nf-core/parabricks modules
(`nvcr.io/nvidia/...`). `conda null` is set with a comment.

[If no semver tags]: TOOL doesn't publish semver Docker tags yet ��
I've opened an issue asking for them: ISSUE_URL. The SHA will be
replaced with a version tag when available.

Is this approach acceptable for TOOL?

---

**2. GPU label — `process_gpu`**  [Only if GPU]

The module uses `label 'process_gpu'` because TOOL requires a CUDA GPU.
Lint flags it as non-standard (not in the standard process_single/low/
medium/high/long set), but `process_gpu` is defined in `nf-core/configs`.

Is `process_gpu` the correct label? Should I also add a secondary standard
label (e.g. `process_high`)?

---

**3. CI tests — GPU not available on GitHub Actions**  [Only if GPU]

Real tests require a GPU and can't run in CI. The module has:
- N stub tests (run in CI — cover output structure and versions)
- N real GPU tests (local-only, tagged `gpu`)

Is stub-only CI acceptable for GPU tools? Are there other GPU modules
I can look at for precedent?

---

PR branch: `USERNAME:BRANCH_NAME`
Thanks!
```

---

## 3. PR Checklist Template (module-specific)

```markdown
# PR Checklist: TOOL/SUBTOOL

Branch: `USERNAME:BRANCH` → `nf-core/modules:master`

## nf-core Standard Checklist

### Description
- [ ] PR description explains what TOOL/SUBTOOL does
- [ ] Links to relevant upstream issue(s): ISSUE_URLS

### Module conventions
- [x] Named `PROCESS_NAME` — matches `{TOOL}_{SUBTOOL}` nf-core convention
- [x] `tag "$meta.id"` present
- [x] Resource label: `process_LABEL`
- [x] `when: task.ext.when == null || task.ext.when` present
- [x] `task.ext.args` used for extra arguments
- [x] `task.ext.prefix` used for output naming
- [x] `stub:` block present and produces all declared outputs

### Container / conda
- [x] Container: `ORG/TOOL:TAG`
- [x] `conda null` with licence comment  [Type B/C]
- [x] `singularity.registry = ''` and `docker.registry = ''` in test config

### Versioning
- [x] Version broadcast via MECHANISM
- [x] `versions.yml` produced in stub block

### Tests
- [x] N stub tests — pass with `--profile conda`
- [x] N real tests — DESCRIPTION OF WHAT THEY TEST

### Lint
- [ ] `nf-core modules lint TOOL/SUBTOOL` → 0 failures, N warnings
- Warnings: EXPLAIN_EACH_WARNING

### Before Opening PR
- [ ] Run `nf-core modules lint TOOL/SUBTOOL` → 0 failures
- [ ] All stub tests pass with `--profile conda`
- [ ] `tests/nextflow.config` has zero local paths
- [ ] Post on nf-core Slack `#new-modules` if non-standard decisions
```
