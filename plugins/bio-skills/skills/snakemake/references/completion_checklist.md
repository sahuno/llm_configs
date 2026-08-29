# Workflow Completion Checklist

Run through this checklist before declaring any workflow complete.

## Workflow Code
- [ ] Dry-run succeeds (`snakemake -n`)
- [ ] Lint passes (`snakemake --lint`)
- [ ] DAG renders correctly (`snakemake --dag | dot -Tpdf > dag.pdf`)
- [ ] All output files exist and are non-empty after a test run
- [ ] Test suite exists (`test/test_config.yaml` + test data) and completes in <5 minutes

## SLURM Profile
- [ ] Profile has `mem_mb: 0` in default-resources
- [ ] Profile has `slurm_account` in default-resources
- [ ] No `mem:` keys anywhere (use `mem_mb_per_cpu` only)
- [ ] `singularity-args:` has no `--` prefix

## Rules
- [ ] All rules that need container packages have `singularity: IMG`
- [ ] Compute-heavy rules have `benchmark:` directive
- [ ] External tool rules have `retries: 2`; script rules have `retries: 0`
- [ ] Intermediate files use `temp()` where appropriate
- [ ] Expensive final outputs use `protected()` where appropriate
- [ ] QC gate rules exist for critical checkpoints

## Scripts
- [ ] Scripts handle `.gz` input transparently
- [ ] Each script ends with `"=== DONE: ... completed successfully ==="`
- [ ] Scripts are testable standalone via argparse CLI

## Config and Reproducibility
- [ ] Config template is documented with REQUIRED/OPTIONAL sections
- [ ] `run_snakemake.sh` is saved in the output directory
- [ ] Config file is copied to the output directory
- [ ] `run_metadata.yaml` is auto-generated
- [ ] `unset SLURM_MEM_PER_NODE` in run script
- [ ] Container image uses pinned version (never `:latest`)
- [ ] No hardcoded absolute paths in the Snakefile (all from config)

## Structure
- [ ] Wildcard-dependent paths use `{sample}` consistently
- [ ] Logs go to `{output_dir}/logs/` with rule name in the filename
- [ ] Benchmarks go to `{output_dir}/benchmarks/`
- [ ] QC outputs go to `{output_dir}/qc/`
- [ ] Rule outputs go to `{output_dir}/results/{rule_name}/`
- [ ] CHANGELOG.md updated with changes
