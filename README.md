At the start of each project load all config and read all files. dir looks something like this `llm_configs`
here's breakdown of files

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
Also make sure not to hard things like contig/chromosome names and sizes to ensure things don't break when we change a something in the configs or sample. get the from the user supplied genome sizes file in the workflow. 

## Initialization
if work if analysis; safely create the folowing dirctories (ie `mkdir -p dir` ) and place files generated under appropriate directories
```
pipelines, analysis, notebooks, data/processed, data/raw, data/metadata, scripts, figures, logs
project_configs, softwares/singularity softwares/singularity/def
```

## Softwares:
You might not have acess to all softwares
use singularity to run comatainers. list of doocker images can be found here `softwares_containers_config.yaml`

### Visualization & Figures 
Create 3 types of figues; png,pdf,svg for analysis
Font type should be Arial. axis should be legible


###### EXAMPLE USE CASE ONLY [BEGIN] ########
USER: You will create a new dir. safely mount only directories  as needed
```

singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/projects/methyl_benchmark_spectrum/ONT_BSseq/ONT_DLP_1stPre/full_spectrum_cohort/pipelines/partialMethylDomains /data1/greenbab/users/ahunos/apps/claude_image/claude.sif

```

singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/projects/methyl_benchmark_spectrum/ONT_BSseq/ONT_DLP_1stPre/full_spectrum_cohort/pipelines/dmr_unphased /data1/greenbab/users/ahunos/apps/claude_image/claude.sif

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

B. I want to select a threshold for hypomethylation for data with bimodal DNA methylation distribution. what are my options? i'm not not the first person doing this so cite some examples


C. add a rule to the pipeline to pick a threshold. the python function is inteligent. for biomodal data allow the user to specify a method but default is lowest valley between the peaks. for unimodal data default is fixed threshold of 0.6. 2. add a rule for genome wide plot of the bins (default: mean) methylation after filtering by the threshold. i want to see everything at a go for the full cohort in addition so each page is a patient and row is all genomewide binned methylation plots belonging to that patient.

D. it would be nice to have window/segment lengths that were merged as part of the columns (last column maybe) in `{STATS_DIR}/merged_hypo_mod{params.mod}/${{sample}}_merged.bed` under rule merge_all_hypomethylated_windows. for example if 2 segments of lenghts 100kb and 150kb were merged capture it as comma-separated value in the column ie `100000,150000`. 
I will need it to compute lengths corrected statistics later on. how would you do this?

###### FOR USERS ONLY [END] ########


FEATURE REQUEST
1. Transition to nextflow
 a. ease resume of failed workflow 
 b. detail logging and workflow metadata
 c. intgration with seqera AI
2. Logging of tasks completed and pending; logging of daily taks done 
3. use `UV` for package management









