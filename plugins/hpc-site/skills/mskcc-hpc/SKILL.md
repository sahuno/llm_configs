---
name: mskcc-hpc
description: |
  Site-specific operational knowledge for the MSKCC HPC cluster (RHEL 8, SLURM,
  account `greenbab`). Use when submitting or debugging SLURM jobs on this
  cluster, choosing a partition, benchmarking with GNU time, deciding between
  an apptainer SIF and a conda env, or serving a local LLM on the iris GPU
  nodes. Covers partition-access rules, slurm-mcp submit_batch quirks, and
  node-level hardware anomalies. NOT portable — every fact here was measured on
  MSKCC hardware and will be wrong on another cluster. On a different site,
  read this only as a template for what to measure.
version: 1.0.0
---

# MSKCC HPC site knowledge

Everything here is measured on one cluster. Treat it as a site log, not as
general HPC advice — `references/apptainer_vs_conda.md` says so explicitly
about its own finding.

## When to read what

| Task | Read | Headline |
|---|---|---|
| Choosing a partition; `sbatch` fails with "Invalid account or account/partition combination" | `references/mskcc_partitions.md` | The cluster default partition `cpu` is **denied** for `greenbab`. There is no working cluster-wide default — set one or always pass `-p`. |
| Submitting through slurm-mcp | `references/slurm_mcp.md` | `submit_batch` injects `--mem`/`--time` on the command line, overriding script directives and conflicting with `--mem-per-cpu`. No `--array` support. |
| Benchmarking runtime / memory | `references/gnu_time.md` | `/usr/bin/time` does not exist on this cluster. Install GNU time via conda and resolve it dynamically. |
| Wrapping samtools/bcftools/htslib in a pipeline | `references/apptainer_vs_conda.md` | The NFS-backed conda env pays a 1–2 M page-fault cold-start tax per fresh node. Prefer the SIF for short high-fan-out rules. |
| Serving a local LLM on iris | `references/vllm_iris.md` | `componc_gpu` is not a valid partition name; L40S 48 GB cannot hold a 30B BF16 model — force `--gres=gpu:a100:1`. |

## Adapting this to another cluster

The *shape* of these findings generalizes even though the values do not. On a
new site, measure and record:

1. Which partitions your account may actually use (`scontrol show partition <p>`
   → check `DenyAccounts`), and whether a usable default exists.
2. Whether `/usr/bin/time` exists, and what benchmark tooling you must install.
3. Where the conda env lives relative to the compute nodes — the SIF-vs-conda
   result is a storage-topology effect, so it flips on a fast parallel FS.
4. Node-level heterogeneity inside a nominally uniform partition. On MSKCC one
   node ran 35 % slower with identical SLURM-visible attributes.

Genome paths, container images, and SLURM profiles for this site live in
`../../profiles/` and are selected by `sites/*.yaml`. See the hpc-site README.
