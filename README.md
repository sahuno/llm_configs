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

## Initialization
ASK USER: What type of work is this session; Ananlysis (Fresh/conituation), software developments

if work if analysis; safely create the folowing dirctories (ie `mkdir -p directoryNames` ) and place all files generated in the sesseion under appropriate directories
```
pipelines, analysis, notebooks, data/processed, data/raw, data/metadata, scripts, figures, logs
project_configs, softwares/singularity softwares/singularity/def
```

## Softwares:
- You might not have acess to all softwares
- use singularity to run containers. list of doocker images can be found here `softwares_containers_config.yaml`





### IGV for genomic track validation
```
singularity exec --bind /data1/greenbab /data1/greenbab/software/images/igver_latest.sif igver \
--input <DMSO_sample_1.bam> <DMSO_sample_2.bam> <DMSO_sample_3.bam> <CKI_sample_1.bam> <CKI_sample_2.bam> <CKI_sample_3.bam> \
-r regions.txt \
-o "results_IGV_plots" \
--dpi 600 -d expand -p 1000 \
--genome 'mm10' --no-singularity && touch results_IGV_plots/done.txt







# example of regions file
bash:iscb012:llm_configs 1014 $ head regions.txt
chr1:148376063-148378679  chr1:148378685-148386192 UID-100_chr1:148375795-148386192
chr1:148375795-148386192    UID-100
chr11:101488764-101551955   mm10_brca1
```




## EXAMPLE USE CASE OF CLUADE CODE FOR COMPUTATIONAL BIO PROJECTS [BEGIN] ########
USER: You will create a new dir. then safely mount only directories  as needed
here's bash function to help mount additional dir 
```
sclaude() {
    local base_mounts="/data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/users/ahunos/blog"
    local container="/data1/greenbab/users/ahunos/apps/containers/claude.sif"
    
    # Join all arguments with commas
    local additional_mounts=""
    if [ $# -gt 0 ]; then
        additional_mounts=$(IFS=,; echo "$*")
        singularity shell -B "${base_mounts},${additional_mounts}" "$container"
    else
        singularity shell -B "$base_mounts" "$container"
    fi
}
```

```

singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/projects/methyl_benchmark_spectrum/ONT_BSseq/ONT_DLP_1stPre/full_spectrum_cohort/pipelines/partialMethylDomains /data1/greenbab/users/ahunos/apps/claude_image/claude.sif

```

singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/data1/greenbab/users/ahunos/blog,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/projects/methyl_benchmark_spectrum/ONT_BSseq/ONT_DLP_1stPre/full_spectrum_cohort/pipelines/dmr_unphased /data1/greenbab/users/ahunos/apps/containers/claude.sif

singularity pull docker://sahuno/claude_gemini_container:latest

singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/data1/greenbab/users/ahunos/blog,/data1/greenbab/users/ahunos/apps/cctrace /data1/greenbab/users/ahunos/apps/containers/claude.sif


##### methylation visualization project
singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/users/ahunos/blog,/data1/greenbab/users/ahunos/apps/workflows/methylation_workflows/methylVis_wf /data1/greenbab/users/ahunos/apps/containers/claude.sif

##### function to run claude singulrity 
sclaude (){
singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/users/ahunos/blog,$1 /data1/greenbab/users/ahunos/apps/containers/claude.sif
}

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



Test 2:
#RNA-Seq pipeline
singularity shell -B /data1/greenbab/users/ahunos/apps/llm_configs,/home/ahunos/miniforge3/envs/snakemake/bin,/data1/greenbab/users/ahunos/apps/workflows/RNA-seq_DiffExpr,/home/ahunos/miniforge3/ /data1/greenbab/users/ahunos/apps/claude_image/claude.sif


Goal: create an R script to perform Differntial gene expression in R with DESEQ2 including volcano plots, gene set enrichment analysis with msigdbr. here are examples from the vignettes you can use.
https://master.bioconductor.org/packages/release/workflows/vignettes/rnaseqGene/inst/doc/rnaseqGene.html

Rscript is here to use; /home/ahunos/miniforge3/envs/r-env/bin/Rscript
instructions: create script for all functions needed 
create run script with optparse to run the fucntions execute all the steps in Deseq

Inputs: counts matrix (column 1 is gene names and rest of columns is sample names), metadata (with samples, condition columns), Reference_group_for_deseq_conditions, sepciesName, vol_pval, gsea_qval 
Outputs: 
structure the directories (main: condition_[tested], subdir: figures, data)
results table, dseq object, meta data, gsea results

here's code i used for gsea in the past. gsea can be tricky
# Get database to use - UPDATED SYNTAX
 specie_type = "Mus musculus",
 msigdbr_db_species = "MM",  
 category_tag = "M2"
 subcategory_tag = "GCP"

    if(!is.null(subcategory_tag)) {
      m_t2g <- msigdbr(db_species=msigdbr_db_species,
                      species = specie_type, 
                       collection = category_tag, 
                       subcollection = subcategory_tag) %>% 
        dplyr::select(gs_name, ncbi_gene)
    } else {
      m_t2g <- msigdbr(db_species=msigdbr_db_species, species = specie_type, 
                       collection = category_tag) %>% 
        dplyr::select(gs_name, ncbi_gene)
    }

start by creating a plan let review
## EXAMPLE USE CASE OF CLUADE CODE FOR COMPUTATIONAL BIO PROJECTS [END] ########


FEATURE REQUEST
1. Transition to nextflow
 a. ease resume of failed workflow 
 b. detail logging and workflow metadata
 c. intgration with seqera AI
2. Logging of tasks completed and pending; logging of daily taks done 
3. use `UV` for python package management









