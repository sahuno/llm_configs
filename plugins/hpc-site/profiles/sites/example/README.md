# Site profile template

Copy this directory, fill in the values, and select it:

```bash
cp -r sites/example sites/my-cluster
export SITE_PROFILE=my-cluster
```

A site profile holds **cluster facts** — reference genomes, container images,
scheduler partitions, bind mounts. These change when you change institution.

Personal preferences go in a **user profile** (`../../users/`) instead, so that
moving institution does not mean rebuilding your plot defaults.

## Files

| File | Holds |
|---|---|
| `paths.yaml` | Roots, container cache, tool checkouts, bind-mount sets |
| `databases.yaml` | Reference genomes — fasta, gtf, chrom.sizes, CpG islands |
| `containers.yaml` | Container images keyed by tool |
| `executor.yaml` | Scheduler defaults: partitions, account, limits |
| `snakemake/` | Snakemake profiles for your scheduler |
| `bashrc_container` | rc file sourced inside the container shell (optional) |

## What to measure on a new cluster

`sites/mskcc-greenbaum/` is a filled-in example, and the `mskcc-hpc` skill
records what was measured to produce it. Its *findings* will not transfer; its
*checklist* will:

1. Which partitions your account may actually use (`scontrol show partition <p>`
   → check `DenyAccounts`), and whether a usable default exists. On the
   reference cluster the cluster-wide default is denied to the lab account, so a
   bare `sbatch` fails.
2. Whether `/usr/bin/time` exists, and what benchmark tooling you must install.
3. Where the conda env lives relative to compute nodes — the SIF-vs-conda
   result is a storage-topology effect and flips on a fast parallel FS.
4. Node heterogeneity inside a nominally uniform partition.
