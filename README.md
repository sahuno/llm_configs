At the start of each project load all config and read all files
here's breakdown of files

1. reference genomes hosted in public aws buckets when hpc files are non available. file include .fasta; .gtf, cpg_islands etc.. 
databases_config.yaml

2. preferences for files and analysis. ie sample sheet format 
setup_preferences.yaml

3. softwares
softwares_containers_config.yaml

4. Executor config such as slurm partition and snakemake profiles & nextflow config
```
executor_config.yaml
```

5. Do not intructions; avoid doing the following activities at all cost
DO_NOT.md


## Initialization
if work if analysis; safely create the folowing dirctories (ie `mkdir -p dir` )
```
pipelines, analysis, notebooks, data/processed, data/raw, data/metadata, scripts, figures, logs
project_configs,
```