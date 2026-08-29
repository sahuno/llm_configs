# bio-guardrails

Hooks that catch the genomics mistakes which are expensive to discover late:
overwritten raw data, silently mixed genome builds, and untagged outputs whose
build you can no longer determine six months on.

## Install

```
/plugin marketplace add sahuno/llm_configs
/plugin install bio-guardrails@sahuno
```

Installing merges these hooks into your config. It does **not** overwrite your
`settings.json` — that was the failure mode of the old `cp`-based install.

## What fires

| Hook | Event | Action | Catches |
|---|---|---|---|
| `block-dangerous-commands.sh` | PreToolUse (Bash) | **block** | `rm -rf` aimed at data dirs |
| `block-raw-data-writes.sh` | PreToolUse (Write/Edit) | **block** | Any write under `data/raw/` |
| `validate-reference-genome.sh` | PreToolUse (Bash, Write/Edit) | **block** | Cross-species mixing, build mixing, `chr`-naming mismatches |
| `enforce-genome-tag.sh` | PreToolUse (Bash, Write/Edit) | **block** | Genomic outputs with no build tag in the filename |
| `snakemake-dryrun.sh` | PostToolUse (Write/Edit) | warn | Runs `snakemake -n` after a `.smk` edit |
| `block-hardcoded-contigs.sh` | PostToolUse (Write/Edit) | warn | Hardcoded chromosome lists |
| `validate-yaml.sh` | PostToolUse (Write/Edit) | warn | Invalid YAML in config files |
| `warn-absolute-paths.sh` | PostToolUse (Write/Edit) | warn | Absolute paths baked into scripts |
| `log-slurm-submission.sh` | PostToolUse (slurm MCP) | log | Appends every submitted job to an audit log |

## Conventions assumed

The blocking hooks enforce a layout. If your projects don't use it, install this
plugin only after reading the scripts — the two that will bite are:

- **`data/raw/` is immutable.** Deposit once, never write again. Transformed
  output goes to `data/processed/`.
- **Genome-build tags are mandatory** on processed genomic files:
  `{sample}.{build}.{description}.{ext}`, under `data/processed/{build}/`.
  Recognized: `mm10`, `mm39`, `GRCm39`, `hg38`, `GRCh38`, `hg19`, `GRCh37`,
  `t2t`, `chm13`. Raw reads, figures, scripts, configs, and logs are exempt.

`/init-bio-project` in the `bio-skills` plugin scaffolds a layout that satisfies
both.

## Site-dependent bits

Two hooks contain a site-specific data root (`/data1/...`) in their match
patterns — `block-dangerous-commands.sh` and `warn-absolute-paths.sh`. Edit
those patterns to your own data root, or they will simply match less.

`log-slurm-submission.sh` already reads `$SLURM_JOB_LOG` and falls back to a
site path; export that variable to redirect the audit log.
