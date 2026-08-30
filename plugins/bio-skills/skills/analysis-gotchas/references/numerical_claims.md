---
tool: process rule
version_observed: "n/a"
date: 2026-05-02
status: active   # active | fixed-upstream | superseded
detect_cmd: ""   # process rule, not tool-specific — nothing to probe
---
# numerical_claims.md — disclosing aggregation method, anchor verification, and doc-vs-code consistency

When citing any aggregated numerical value (mean %, median, mean coverage, mutation rate, summary statistic across CpGs / genes / cells / samples / regions) in a doc, figure caption, manuscript, or project log, the **aggregation method must be stated explicitly alongside the number**. The same data aggregated by different methods can differ by 5–20 %; an implicit method is not reproducible by a reviewer, a collaborator, or future-you in 6 months.

## In code (the script that produces the number)

- **Docstring or top comment must name the aggregation method explicitly.** Not "computes mean methylation"; say "simple mean of per-CpG percent_modified, min_coverage = 1" OR "weighted: sum(nmod) / sum(nvalid_cov), min_coverage = 5". Method name + filter + threshold.
- **The output TSV must include the unit-count column** (`n_cpgs`, `n_reads`, `n_cells`, `n_samples`, etc.) so a reader can recompute the alternative metric without re-running.
- **If both methods are routinely interesting, output both columns.** This is what `aggregate_ltr_methylation.py` does — `weighted_pct` alongside `simple_mean_pct`. Costs nothing extra to compute, prevents method-mismatch bugs entirely.

## In docs / manuscripts / project logs (anywhere citing the number)

- Use a parenthetical that names method + filter + unit count: "body 5mC = 63.26 % (simple mean across 215 CpGs, min_coverage = 1)" — not just "body 5mC = 63.26 %".
- If the doc and code disagree on the method, **the code is ground truth** — fix the doc, not the code.

## Anchor verification when reproducing a doc-cited or previously-published number

Hard-code the reference value in the script and assert the new computation matches within tolerance. Failing the anchor means one of {doc is wrong, code is wrong, data changed} — investigate before writing the new value to a cohort table. Pattern:

```python
ANCHOR = {"5p_LTR": 10.57, "body": 63.26, "3p_LTR": 0.00}  # method: simple_mean, min_cov=1
TOLERANCE = 0.5
for region, expected in ANCHOR.items():
    observed = compute(region)
    assert abs(observed - expected) <= TOLERANCE, \
        f"ANCHOR FAIL {region}: expected {expected}, got {observed:.2f}"
```

The verification result should be written alongside the cohort output as `anchor_check_<basename>.tsv` (one row per anchor with expected / observed / diff / pass) so the check is auditable without re-running.

## Worked failure modes

- **2026-05-02, ATLL Project_17424**: operational doc reported "body 5mC = 63.26 %" alongside the description "(sum_mod / sum_nvalid)" — the weighted method. The number was correct, but it had actually been computed by simple-mean-per-CpG. A reviewer trying to reproduce 63.26 % via the documented weighted method would have computed 58.05 % (a 5 % drift on the same data) and reasonably concluded the analysis was broken. Caught only because the new cohort aggregation script ran explicit anchor verification on **both** methods and logged the discrepancy. Fix: doc updated to specify simple-mean; cohort TSV reports both metrics; both methods now in `results/.../scripts/aggregate_ltr_methylation.py` permanently.
