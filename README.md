At the start of each project load all config and read all files. dir looks something like this `llm_configs`
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

5. Pay attention to DO NOT intructions; avoid doing the following activities at all cost
DO_NOT.md


## Initialization
if work if analysis; safely create the folowing dirctories (ie `mkdir -p dir` )
```
pipelines, analysis, notebooks, data/processed, data/raw, data/metadata, scripts, figures, logs
project_configs,
```


###### EXAMPLE USE CASE ONLY [BEGIN] ########
USER: You will create a new dir. safely mount only directories  as needed
```
singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/data1/greenbab/projects/methyl_benchmark_spectrum/ONT_BSseq/ONT_DLP_1stPre/full_spectrum_cohort/pipelines/partialMethylDomains /data1/greenbab/users/ahunos/apps/claude_image/claude.sif
```

CLAUDE PROMPT 0: 
    please load `/data1/greenbab/users/ahunos/apps/llm_configs` which has detailed info for the working

CLAUDE PROMPT 1: 
    create &/or Update a claude md file with apporapriate task list to accomplish these goals 

SESSION_TYPE: Analysis
GOALS:
A. Create a snakemake workflow for partial_methylated_domains with the rules
1. bin the genome with user supplied window size and offset
2. Windows that intersect CpG islands (CGIs) or UCSC gap regions should be discarded
3. use bedtools map to overlaps with DNA methylation data (modkit bedmethyl) of each sample & compute the mean, meadian, stdev,count,collapse   
example code i used previously
```
bedtools map \
          -a {params.windows} \
          -b {input.sample_bed} \
          -c 11,11,11,11 \
          -o mean,median,count,collapse 
```
allow user filter what type of modification in the bedmethyl ie. m, h, a
4. plot the distribution of mean methylation per bin for all samples on the same page but different panels. clearly label each sample with clear indication of which conditions.
5. create multiple statistics matrix with rows=windows, columns=samples, values=one of the stats you computed before ` mean, meadian, stdev,count,collapse`

create configs with default been hg19, user would change over time.
input is a tsv sample_sheet `nanoseq_dorados_samples_spectrum.csv`
use singularity for snakemake with approprorate workflow profile

B. 
###### FOR USERS ONLY [END] ########
