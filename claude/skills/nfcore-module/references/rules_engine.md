# Rules Engine — nf-core Module Builder

Source of truth for all hard rules. Read this at skill start.
Derived from building dorado/basecaller, modkit/localize, modkit/localize/plot.

---

## R1 — ext Keys (LINT FAILURE if violated)

Only these `ext` keys are allowed in `main.nf`:
| Allowed | Purpose |
|---------|---------|
| `ext.args` | Primary tool arguments |
| `ext.args2` | Second tool call arguments |
| `ext.args3` | Third tool call arguments |
| `ext.prefix` | Output filename prefix |
| `ext.when` | Conditional execution |

**Never use**: `ext.device`, `ext.model`, `ext.threads`, `ext.models_dir`, or any other custom key.
**Fix**: hardcode sensible defaults in the script body.
```groovy
// ❌ Fails lint
--device ${task.ext.device ?: 'cuda:all'}

// ✅ Passes lint — users override via ext.args if needed
--device cuda:all
```

---

## R2 — tests/nextflow.config Must Be Portable

This file ships with the module and runs on CI and every reviewer's machine.
Zero local paths. Zero SIF overrides. Zero absolute references.

```groovy
// ✅ Correct minimal config
process {
    withName: 'TOOL_SUBTOOL' {
        ext.args = params.module_args ?: ''
    }
}
singularity.registry = ''
docker.registry      = ''
// GPU only:
singularity.runOptions = '--nv'
```

**Never add (any of these are a violation):**
- `container = '/data/...sif'` — overrides module container for everyone
- `params { test_reference = '/absolute/path' }` — breaks all non-local runs
- `params { test_bam = ... }` or any ad-hoc `params {}` block — workaround smell
- `models_dir = '...'` — local models, won't exist in CI
- `// container = /path/to/local/...sif` — even commented-out local paths must be removed; reviewers will flag them

**Also check tests/main.nf.test:**
- `${projectDir}/tests/...` or `file("${projectDir}/...")` as a test input path — machine-local, breaks CI
- Use `params.modules_testdata_base_path + 'path/to/file'` (concatenation) for all test inputs

### ⚠ R2 Audit — Run This Before Phase 5

Before moving to PR artifacts, explicitly audit the test files. If any violation is found, fix and re-test:

```bash
# Check nextflow.config for banned patterns
grep -n 'projectDir\|test_bam\|test_reference\|models_dir\|\.sif' \
  modules/nf-core/<tool>/<subtool>/tests/nextflow.config

# Check test file for hardcoded local paths
grep -n 'projectDir\|/data/\|/home/' \
  modules/nf-core/<tool>/<subtool>/tests/main.nf.test
```

Expected output: **nothing**. If anything is printed, remove it before proceeding.

> Why: these patterns are invisible to lint, pass tests locally, and only break on CI or
> a reviewer's machine. They're the most common reason a well-intentioned module gets
> rejected or breaks nf-core CI silently.

---

## R3 — Test Data: Real Data Only

Never generate synthetic test data. If the user hasn't provided test data, block:
> "I need real test data to write working tests. Please provide at least one input
> file path. Synthetic data produces meaningless tests and can mask real bugs."

---

## R4 — params.modules_testdata_base_path Concatenation

`${params.modules_testdata_base_path}` is `null` in nf-test's Groovy rendering context.
It only resolves at Nextflow runtime. Use concatenation:

```groovy
// ✅ resolves at Nextflow runtime
file(params.modules_testdata_base_path + 'genomics/homo_sapiens/genome/genome.fasta',
     checkIfExists: true)

// ❌ params is null → 'nullgenomics/...' → file not found
file("${params.modules_testdata_base_path}genomics/homo_sapiens/genome/genome.fasta",
     checkIfExists: true)
```

---

## R5 — nf-test Assertions: Channels Not Paths

nf-test's `path()` returns a Java `Path` which has no `.isDirectory()` method.
Check output channels instead:

```groovy
// ✅
{ assert process.out.bam }
{ assert process.out.png }

// ❌ MissingMethodException: no .isDirectory() on UnixPath
{ assert path("figures/png").isDirectory() }
```

---

## R6 — GPU Module Rules

1. Use `label 'process_gpu'` (defined in nf-core/configs; lint warns, not fails — acceptable)
2. Add `singularity.runOptions = '--nv'` in `tests/nextflow.config`
3. Tag real GPU tests: `tag "gpu"` — these are excluded from CI
4. Stub tests must pass with `--profile conda` (no GPU needed)
5. To run GPU tests locally: `--profile singularity,gpu --tag gpu`
6. The `gpu` profile comes from `tests/config/nf-test.config` (global repo config) — it sets `--nv`

---

## R7 — Container Rules by Module Type

**Type A (bioconda):**
```groovy
conda "${moduleDir}/environment.yml"
container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/tool:version--hash' :
    'quay.io/biocontainers/tool:version--hash' }"
```

**Type B (licensed, no bioconda):**
```groovy
// <tool> is not on bioconda (<REASON> licence).
// Using official Docker Hub image — same pattern as nf-core/parabricks modules.
// Tracking semver tags: <upstream_issue_url>
conda null
container "<org>/<tool>:<sha_or_version>"
```

**Type C (GPU):**
Same as Type B but add `label 'process_gpu'` and `--nv` in test config.
Use the official upstream CUDA-enabled image.

**Type D (R/Python script):**
```groovy
conda "${moduleDir}/environment.yml"
container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://wave.seqera.io/wt/<token>/wave/build:<tag>' :
    'wave.seqera.io/wt/<token>/wave/build:<tag>' }"
```
Build Wave URI with: `wave -f <environment.yml_dir> --tower-token $TOWER_ACCESS_TOKEN`

---

## R8 — Version Broadcasting

**Type A/D (conda available):**
```groovy
cat <<-END_VERSIONS > versions.yml
"${task.process}":
    tool: \$(tool --version 2>&1 | sed 's/tool version //')
END_VERSIONS
```

**Type B/C (conda null):**
```groovy
// In output block:
tuple val("${task.process}"), val('tool'), eval("tool --version 2>&1 | head -1"), emit: versions_tool, topic: versions

// In stub block — hardcode (eval() doesn't run in stub):
cat <<-END_VERSIONS > versions.yml
"${task.process}":
    tool: 1.4.0
END_VERSIONS
```
Run `nf-core modules lint --fix` to auto-add `topics:` to meta.yml.

---

## R9 — Groovy Template Escaping (Type D only)

When using `template 'script.R'`, Nextflow renders as a Groovy template:

| In template | Rendered in R/Python | Purpose |
|-------------|---------------------|---------|
| `$variable` | value substituted | Groovy variable |
| `\$literal` | `$` | literal dollar sign |
| `\\\\` | `\\` | single backslash |
| `sep = "\t"` | `sep = "\t"` ✅ | tab character |
| `sep = "\\t"` | `sep = "\\t"` ❌ | two-char string, NOT a tab |

**SE guard for R loess** — single sample per condition → `sd()` = NA → `loess()` crashes:
```r
if (all(is.na(se_vals))) {
    smooth_se_vals <- rep(0, nrow(.SD))
} else {
    fit_se <- loess(se_pct ~ offset, data = .SD[!is.na(se_pct)], span = l_span)
    smooth_se_vals <- predict(fit_se, newdata = .SD)
}
```

---

## R10 — gitignore Entries

Always add to `.gitignore` before first commit:
```
**/sandbox/
modules/nf-core/<tool>/<subtool>/tests/data/models/
```

Do not commit: model weights, reference genomes, large BAMs, SIF files.
