
----------------------------------------------------------------------------------------------------
# Project one:  
## Bionformatics analysis project initialization/set up
```
mkdir -p softwares/{bin,containers} \
data/{archived,exdata,inbox,processed,raw,validation} \
workflows/wf_snakemake/{configs,docs,profiles/slurm,rules,scripts} \
sandbox logs src/{models,features} tests \
docs/{deepResearch,manuscript/{figures/{png,pdf,svg,scripts,archived},writeup}} \
results/v1_[description]

## create a 
touch data/README.md (description of data)
touch README.md (tree or dir structure, project goals, approaches, )
touch workflows/wf_snakemake/README.md
touch .gitignore
```

## descriptions
softwares/bin - softwares that may be needed for analysis
softwares/containers - .def files, images including third-party containers needed to run analysis
docs/manuscript/{figures/{png,pdf,svg,scripts,archived}} - multi-panel figures collated with python scripts on letter size paper size.  This NOT a substitue for results/v1_[description]/figures
docs/manuscript/figures/archived - all figures no longer in use 



## discussion with claude
1. script to create these dir? of git pull these dir each time? or can we have git clone first option and a local fall back?  
----------------------------------------------------------------------------------------------------

figure rubrics
'''
- are the axis legible 
- truncated labels on figures, (title, facet labels)
- 
'''



### claude review response
'''

● Good question. Let me compare the three sources of truth you have and give you an honest assessment.                                                                          
                                                                                                                                                                                
  The core problem: three divergent structures                                                                                                                                  
                                                                                                                                                                                
  ┌─────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐                          
  │     Source      │                                                           Structure                                                            │                        
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                          
  │ CLAUDE.md §1.5  │ data/{inbox,raw,processed}, src/, results/, figures/{png,pdf,svg}/, workflows/                                                 │
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ scratch.md      │ softwares/{bin,containers}, data/{archived,exdata,inbox,processed,raw,validation}, docs/manuscript/figures/..., sandbox        │
  ├─────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ init_project.py │ data/{raw,processed,external,metadata}, notebooks/, src/{data,features,models,visualization}, results/{figures,models,reports} │
  └─────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  These have drifted apart. The script doesn't implement the CLAUDE.md spec, and the scratch notes propose a third variant. That's the real issue before anything else.

  What's over-engineered

  - src/{models,features,visualization} — ML subdirs. Most bioinfo projects are a flat src/ with numbered scripts. You'll create 4 empty directories and never use 3 of them.
  - notebooks/exploratory vs notebooks/reports — premature split. You rarely have enough notebooks to justify this.
  - data/validation, data/archived — unclear what goes here vs data/processed/. More dirs = more decisions about where to put things.
  - docs/manuscript/writeup/{methods,results} — you'll write the manuscript in Word/Overleaf, not in a directory tree. These will stay empty.
  - sandbox — if everything else is well-organized, what's sandbox for?
  - README in every directory — 15+ boilerplate READMEs that immediately go stale. Better: one good top-level README with a tree diagram.

  What's actually missing (the useful stuff)

  1. .gitignore template — critical. Every genomics project needs to exclude *.bam, *.pod5, *.fast5, *.cram, *.sif, data/raw/, etc. from day one. This is the single
  highest-value generated file.
  2. sample_sheet.tsv template — your CLAUDE.md already defines the format (patient, sample, condition, path, genome). Generate a blank one with the header row.
  3. Genome build parameter — the script takes --name but doesn't ask which genome. Every downstream path depends on this (data/processed/{genome_build}/).
  4. Config template — a starter config.yaml that points to the database paths from profiles/databases/databases_config.yaml for the chosen genome.
  5. environment.yaml or requirements.txt — reproducibility from minute one.
  6. Project type parameter — not every project needs workflows/wf_snakemake/. A DGE analysis needs different dirs than a variant calling pipeline.
  7. Figures location is inconsistent — CLAUDE.md says root-level figures/{png,pdf,svg}/, scratch.md puts them under docs/manuscript/, init_project.py puts them under
  results/figures. Pick one.

  What I'd actually build

  A lean, parameterized initializer:

  init_project --name my_project --type {analysis,pipeline,ml} --genome {mm10,hg38,...}

  Core (always created):
  my_project/
  ├── .gitignore              # pre-populated for genomics
  ├── README.md               # project name, date, aims, tree
  ├── config.yaml             # genome paths, parameters
  ├── sample_sheet.tsv        # header row only
  ├── data/raw/
  ├── data/processed/{genome}/
  ├── src/
  ├── results/v1/
  ├── figures/{png,pdf,svg}/
  ├── logs/
  └── docs/

  Added by --type pipeline:
  ├── workflows/wf_snakemake/{Snakefile,profiles/slurm/config.yaml}
  ├── softwares/containers/

  Added by --type ml:
  ├── src/models/
  ├── src/features/
  ├── notebooks/

  That's it. ~10-12 directories for most projects instead of 25+. Directories you don't create don't need explaining.

  Bottom line

  Your scratch.md instinct is right — the current init_project.py is a generic data-science template that doesn't match how you actually work. But the fix isn't adding more
  directories (scratch.md's version is even bigger). It's:

  1. Reconcile to one canonical structure (update CLAUDE.md, delete the others)
  2. Parameterize by project type so you're not scaffolding ML dirs for a methylation analysis
  3. Generate useful files (.gitignore, sample_sheet, config) instead of empty READMEs
  4. Start minimal, mkdir as needed — an empty directory has zero value

  Want me to build the updated script?

'''