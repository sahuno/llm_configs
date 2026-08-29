# Analysis recipes

Cookbook for the three analytical operations every study needs: variance
partitioning, model fitting + validation, and cost accounting.

## 1. Variance partitioning (Stage 7)

Goal: tell the user **how much of the wall-time variance is real signal
(condition effects) vs noise (replicate-to-replicate) vs hardware drift
(host-to-host)**. If host explains > 25 % of variance, the partition is
heterogeneous and you need `--exclude=<bad_nodes>` or a tighter pool.

### R approach (preferred)

```r
library(lme4)
library(lmerTest)

df <- read.csv("benchmark.csv")
fit <- lmer(wall_s ~ factor1 + factor2 + factor3 + (1 | host), data = df)
vc <- VarCorr(fit)
res_var <- attr(vc, "sc")^2
host_var <- vc$host[1]
cond_var <- var(predict(fit, re.form = NA))     # variance explained by fixed effects

total <- res_var + host_var + cond_var
data.frame(
  source = c("condition (fixed)", "host (random)", "replicate (residual)"),
  variance = c(cond_var, host_var, res_var),
  pct = c(cond_var, host_var, res_var) / total * 100
)
```

### Python approach

```python
import statsmodels.formula.api as smf
import pandas as pd

df = pd.read_csv("benchmark.csv")
md = smf.mixedlm("wall_s ~ factor1 + factor2", df, groups=df["host"])
fit = md.fit()
print(fit.summary())
# fit.cov_re   = host random-effect variance
# fit.scale    = residual variance
```

### Decision rules

| host_pct | What to do |
|---|---|
| < 10 % | Hardware homogeneous, proceed |
| 10–25 % | Note in REPORT.md caveats; consider re-running outliers on alternate nodes |
| > 25 % | Stop — find the heterogeneous nodes, exclude, rerun affected stages |

### Detecting outlier nodes

If host variance is high, identify *which* host(s) are responsible:

```r
# Per-host residuals
df$resid <- residuals(fit)
aggregate(resid ~ host, df, function(x) c(mean = mean(x), sd = sd(x)))
```

A host with `mean_resid > 2 × residual_sd` is a strong outlier (this caught
isca071 in the samtools sort study at +35 % wall).

## 2. Model fitting + out-of-sample validation (Stages 5, 6)

### One-term linear model (default — try first)

```python
import numpy as np
import pandas as pd

df = pd.read_csv("benchmark.csv")
N = df["n_records"].values
T = df["wall_s"].values

# Stack design matrix
A = np.vstack([np.ones_like(N), N]).T
coefs, residuals, rank, sv = np.linalg.lstsq(A, T, rcond=None)
a, b = coefs
T_pred = A @ coefs
r2 = 1 - np.sum((T - T_pred)**2) / np.sum((T - T.mean())**2)
print(f"wall_s = {a:.3f} + {b*1e6:.3f} us/record * N    R^2 = {r2:.4f}")
```

### Two-term model (when 1-term fails validation)

If 1-term has > ±20 % error on held-out data, refit with file_size as a
second predictor. Discovered in the samtools sort study — page-cache vs
I/O-bound regimes don't fit a single linear-in-N curve.

```python
A = np.vstack([np.ones_like(N), N, df["file_size_bytes"].values]).T
coefs2, *_ = np.linalg.lstsq(A, T, rcond=None)
a, b, c = coefs2     # wall_s = a + b*N + c*file_size
```

The 2-term coefficient `b` may go *negative* — that's a collinearity
artefact (file_size ≈ K × N), not a real mechanism. Don't interpret in
isolation. The validation R² and out-of-sample residuals are what matter.

### Out-of-sample validation protocol

```python
# Held-out inputs (Stage 6)
holdout = pd.read_csv("stage5_validate/benchmark.csv")
N_h = holdout["n_records"].values
T_h_obs = holdout["wall_s"].values
T_h_pred = a + b * N_h + c * holdout["file_size_bytes"].values   # 2-term
err_pct = 100 * (T_h_obs - T_h_pred) / T_h_pred

print(holdout.assign(predicted=T_h_pred, error_pct=err_pct))
```

| Median |error_pct| | Verdict |
|---|---|
| < 10 % | Production-ready; ship `model.yaml` |
| 10–20 % | Add caveats; safe direction = over-prediction is fine |
| > 20 % | Refit with 2-term or non-linear; investigate regime |

## 3. Cost accounting (Stage 7)

Convert wall × threads × $/core-hour into per-sample cost. Frequently the
fastest config is *not* the cheapest.

### Compute per-condition cost

```python
import pandas as pd

df = pd.read_csv("benchmark.csv")
COST_PER_CORE_HOUR = 0.05   # default; user-configurable

df["cpu_hours"] = df["wall_s"] / 3600 * df["threads"]
df["cost_usd"]  = df["cpu_hours"] * COST_PER_CORE_HOUR

per_cond = df.groupby(["threads", "mem_per_thread", "compression"]).agg(
    n=("wall_s", "size"),
    wall_med=("wall_s", "median"),
    cost_med=("cost_usd", "median"),
).reset_index()
print(per_cond.sort_values("cost_med"))
```

### Identify the cost-Pareto frontier

A condition is on the **cost-Pareto frontier** if no other condition is
both cheaper *and* faster. The frontier is the set of optimal trade-offs.

```python
# Sort by wall ascending; keep only points where cost is strictly
# decreasing (or equal) as wall increases
per_cond = per_cond.sort_values("wall_med")
pareto = []
min_cost = float("inf")
for _, row in per_cond[::-1].iterrows():   # iterate slowest-first
    if row["cost_med"] < min_cost:
        pareto.append(row)
        min_cost = row["cost_med"]
pareto = pd.DataFrame(pareto[::-1])
print("Cost-Pareto frontier:\n", pareto)
```

### Reporting

In `REPORT.md` §7, produce:

1. A scatter plot of `wall_med` (x) vs `cost_med` (y), colour-coded by
   threads. Highlight the Pareto frontier.
2. A table with the recommended config, the cost-cheapest config, and the
   wall-fastest config. Often `-@ 16` is on the frontier alongside `-@ 32`.
3. The cost-per-sample for the recommended config at the user's expected
   throughput (e.g., "1 sample = $X; 100 samples = $Y").

### Default rate

Use `$0.05/core-hour` if the user doesn't supply a local rate. This is a
reasonable estimate for shared academic HPC; cloud is usually higher.

## Variance vs cost trade-off

When CV is high (> 20 %) at the recommended config, the cost estimate has
the same uncertainty as wall — propagate it:

```python
cost_lo = wall_min * threads / 3600 * COST_PER_CORE_HOUR
cost_hi = wall_max * threads / 3600 * COST_PER_CORE_HOUR
print(f"Cost range: ${cost_lo:.4f} - ${cost_hi:.4f} per sample")
```

This is honest — pretending cost is a point estimate when wall has 20 % CV
is misleading.
