# This is collection of principles to work with AI coding agents

At the start of each project load all config and read all files. dir looks something like this `llm_configs`
here's breakdown of files

# Directory Structure of llm_configs


1. reference genomes hosted in public aws buckets when hpc files are non available. file include .fasta; .gtf, cpg_islands etc.. 
databases_config.yaml

2. preferences for files and analysis. ie sample sheet format 
setup_preferences.yaml

3. softwares; list to softwares/singularity images that can be used
softwares_containers_config.yaml

4. Executor config such as slurm partition and snakemake profiles & nextflow config
```
executor_config.yaml
```

5. Pay attention to DO NOT intructions; avoid doing the following activities at all cost
DO_NOT.md


## Softwares:
- You might not have acess to all softwares
- use singularity to run containers. list of doocker images can be found here `softwares_containers_config.yaml`













#########CLAUDE: DONOT DELETE##########################
FEATURE REQUEST
1. Transition to nextflow
 a. ease resume of failed workflow 
 b. detail logging and workflow metadata
 c. intgration with seqera AI
2. Logging of tasks completed and pending; logging of daily taks done 
3. use `UV` for python package management
#######################################################







