# AI agents (coding) for scientific discovery

At the start of each project load all config and read all files. 

# Quick start
- copy over `claude/CLAUDE.md` file into your home or parent of your project directory
```
claude/CLAUDE.md
```

# Directory Structure of llm_configs
directory looks something like this `llm_configs`
here's breakdown of files

```
bash:iscb012:share 1089 $ tree .
.
├── Best_practices.md
├── claude
│   ├── agents
│   │   └── figure-editor.md
│   ├── CLAUDE.md
│   ├── hooks.yaml
│   ├── mcps
│   │   └── mcps.md
│   ├── profiles
│   │   ├── bash_profiles
│   │   │   └── bashrc_iris_link -> /home/ahunos/.bashrc
│   │   ├── databases
│   │   │   └── databases_config.yaml
│   │   ├── DO_NOT.md
│   │   ├── programming_language_profiles
│   │   │   ├── python
│   │   │   │   └── matplotlib
│   │   │   │       └── matplotlib_defaults
│   │   │   └── R
│   │   ├── setup_preferences.yaml
│   │   ├── software_configs
│   │   │   └── softwares_containers_config.yaml
│   │   └── workflow_profiles
│   │       ├── executor_config.yaml
│   │       ├── nextflow
│   │       └── snakemakes
│   │           ├── slurmConfig
│   │           │   └── config.yaml
│   │           └── slurmMinimal
│   │               └── config.yaml
│   ├── PROMPTS.md
│   ├── README.md
│   └── scripts
│       ├── check_genome_consistency.py
│       ├── check_sample_sheet.py
│       ├── init_project.py
│       └── validate_config_params.py
├── cli_coding_agents_setups
├── examples
│   └── examples.md
└── README.md

19 directories, 22 files
```

- databases_config.yaml
    - reference genomes hosted in public aws buckets when hpc files are non available. file include .fasta; .gtf, cpg_islands etc.. 

- setup_preferences.yaml
    - preferences for files and analysis. ie sample sheet format 

- softwares_containers_config.yaml
    - softwares; list to softwares including paths and links singularity & docker images that can be used for analysis


4. Executor config such as slurm partition and snakemake profiles & nextflow config
```
executor_config.yaml
```

5. Pay attention to DO NOT intructions; avoid doing the following activities at all cost
DO_NOT.md


## Softwares:
- Claude code might not have acess to all softwares.
- use singularity to run containers. list of docker images can be found here `softwares_containers_config.yaml`














FEATURE REQUEST
1. Transition to nextflow
 a. ease resume of failed workflow 
 b. detail logging and workflow metadata
 c. intgration with seqera AI
2. Logging of tasks completed and pending; logging of daily taks done 
3. use `UV` for python package management









