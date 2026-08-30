---
tool: glmnet::cv.glmnet
version_observed: "unrecorded"
date: 2026-04-29
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  rerun with K>=5 seeds; compare selected lambda and per-gene Q2 across seeds
---
# Regularized CV at small n (n < 50): seed instability, q-floors, degenerate r

These bite together when running cv.glmnet (or any nested-CV regularized regressor) at small n. Confirmed during the SU2C DNAme × RNA modelling sweep (n=36, 2026-04-29) — same data, same code, same nominal seed, very different "results" depending on which knob you trusted.

## 1. cv.glmnet at small n is seed-fragile; never publish a single-seed Q²
- **Symptom**: NLRC5 swung Q² = +0.062 → −0.060 → +0.0004 ± 0.056 across runs of identical code with identical `set.seed(42)`. Same data, same hyperparameter grid, same software version.
- **Why**: cv.glmnet's inner-CV folds are RNG-driven. Inside `mclapply` workers the RNG state is consumed in worker-scheduling order, so each gene's chosen `lambda.min` depends on *which fork picks up which gene first* — a `set.seed()` in the parent process never reaches the per-fork fit deterministically.
- **How to apply**: any cv.glmnet (or comparable regularized-CV) result at n < 50 must be paired with K ≥ 5 seed reruns and reported as **mean ± sd**, not peak. A single Q² value is meaningless without seed variance. Pattern: see `scripts/27_elasticnet_seed_stability.R` in the SU2C DNAme project for a reference seed-sweep harness.

## 2. K permutations imposes a hard q-floor — predict it before picking K
- **Formula**: `q_min ≈ (1 / (1 + N_null)) × n_tests / 2` (BH at the smallest possible empirical p with rank 2).
- At K=10 perms × 15K genes × 1 alpha each = 150K null draws, n_tests=15K → `q_min ≈ 0.0500`. **No gene can achieve q < 0.05** even with infinite signal — the BH numerator floors out at 1/150,450.
- We hit this exactly: NR5A1, ENPP6, CDH17, CKMT2 all stuck at q = 0.0500 (each beat every null draw; q just couldn't go lower).
- **How to apply**: before submitting permutation jobs, compute predicted `q_min` and decide if it crosses the desired threshold. For strict q < 0.05 at 15K tests need K ≥ 30. K = 100 is overkill (diminishing returns).

## 3. Pearson r on near-constant LOOCV predictions is degenerate
- **Symptom**: B2M ridge gave r = −1.000 with Q² = −0.060. HLA-A similarly. r reads "perfect anti-correlation"; reality is "ridge collapsed predictions to the cohort mean."
- **Why**: when ridge shrinks predictions to ≈ ȳ, residual variation has tiny sd; `cor()` happens to align ±1 with y by coincidence. Mathematically valid, biologically meaningless.
- **How to apply**: when reporting Pearson r alongside Q², gate on `sd(yhat_loo) > 0.05 * sd(y)` (or similar fraction). Otherwise report r as NA. Q² is the honest metric in degenerate cases.

## 4. Pooled-null exchangeability is an assumption — verify with λ_GC
- We pool null Q² across genes (different p_g) within each α to get N_null = 150K from K=10 reruns. At small n the null Q² distribution depends mildly on p_g.
- **Why we got away with it**: cv.glmnet-with-`lambda.min` controls overfit similarly across p_g; observed λ_GC = 0.98–1.09 across α (well-calibrated).
- **How to apply**: always compute λ_GC after pooled-null FDR. λ_GC > 1.2 → split null by p_g bins instead of pooling, or commit to per-gene K ≥ 100. λ_GC < 0.8 → null is over-dispersed; the test is conservative.

## Cross-references
- `references/parallel_r_oom.md` — for the per-iteration `gc()` pattern that prevents the silent fork-drop failure mode that compounds seed instability.
