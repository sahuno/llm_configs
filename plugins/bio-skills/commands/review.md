---
description: Adversarial review of code written this session — data integrity, genome safety, pipeline correctness, statistical rigor, reproducibility
argument-hint: [path or "session"]
---

Review all code written or modified in this session — or at `$ARGUMENTS` if a
path is given — with fresh eyes. Your job is to **find problems**, not to
confirm the work is fine. A review that finds nothing should say what it checked
and why each category came back clean.

For every issue: file, line, category, severity (**critical** / **warning** /
**note**), the concrete failure it causes, and the fix.

### 1. Data integrity
- Is raw data ever modified or overwritten?
- Are input and output paths distinct — no read-then-write to the same file?
- Are random seeds set for every stochastic operation?

### 2. Genome build safety
- Are contig names or sizes hardcoded anywhere?
- Does every genomic output carry the build in both filename and directory?
- If multiple builds are involved, is the liftOver verified — unmapped regions
  checked, both coordinate sets retained?
- Do reference paths come from `$SITE_CONFIG/databases.yaml` rather than literals?

### 3. Pipeline correctness (Snakemake / Nextflow)
- Do rules with a `singularity:`/`container:` directive avoid a nested
  `singularity exec` in the shell block?
- Are resources (`mem_mb_per_cpu`, threads, GPU) plausible for the work?
- Does a dry run pass? Are all input/output declarations complete?
- Are sample names parsed safely — no whitespace, no special characters?

### 4. Statistical rigor
- Is multiple-testing correction applied, and is it the right one? Default is
  Benjamini–Hochberg for discovery; Bonferroni only for a small pre-specified
  confirmatory set.
- Are effect sizes reported alongside p-values?
- Is the test appropriate for the data's distribution, coverage and n?
- At n < 50 with regularized CV, is seed stability checked? See the
  `analysis-gotchas` skill.

### 5. ONT-specific (if applicable)
- Does the dorado model match the sequencing chemistry?
- Does `modkit pileup --ref` match the alignment reference?
- Are multi-run samples basecalled independently and merged after alignment?

### 6. Reproducibility
- Any hardcoded absolute paths?
- Are container and tool versions pinned or read from config?
- Would this produce identical results tomorrow, on a different node?

### 7. Forbidden patterns
- Variable names shadowing builtins: `conditions`, `counts`, `results`, `sum`,
  `median`, `mean`
- `snakemake --reason` (does not exist)
- Missing author/date header on a script

### 8. Silent failure
- For any long parallel job: was it *verified* or merely completed? Run
  `/verify-run`. `mclapply` drops OOM-killed forks as `NULL` while the parent
  exits 0.

## Output

| File | Line | Category | Severity | Issue | Fix |
|------|------|----------|----------|-------|-----|

Then a one-line verdict: safe to proceed, or the critical items blocking it.
