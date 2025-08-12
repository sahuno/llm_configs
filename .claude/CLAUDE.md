# [MUST BE USED] Main Claude Configuration
## About 
    --- 
    Project Type: [Fill]
    Session (New or continuation)
    Author (default): Samuel Ahuno (ekwame001@gmail.com) 
    ---
- Note to Claude: if the user does not fill this out, interview them to do so and then remove this line.
- ASK USER: What type of work this session is and whether its new or conituation of current project? 
Bioinformatics Ananlysis, software developments, Writing (Blogs/Journal), Maths (Applied or pure) (Fresh/conituation)


## Key Principles
---
### 1. Reproducibility First
- **Never modify raw data** - All data transformations should create new files
- **Version control everything** - Use git for code, DVC or git-lfs for large data files
- **Document dependencies explicitly** - Use requirements.txt, environment.yml, or apptainer/singularity
- **Set random seeds** - Always set seeds for any stochastic processes
- **Use relative paths** - Never hardcode absolute paths

### 2. Workflow Organization
- **One-way data flow** - Data moves from raw → processed → results
- **Modular functions** - Each function should do one thing well
- **Pipeline automation** - Use Snakemake, Nextflow, or Make for complex workflows
- **Clear naming** - Use descriptive names: `01_download_data.py`, `02_clean_sequences.py`

### 3. Documentation Standards
- **README for every directory** - Explain what each folder contains
- **Docstrings for all functions** - Include parameters, returns, and examples
- **Author and date** - Add author and date to all scripts and documents
- **Computational notebooks** - Balance between documentation and code
- **Method documentation** - Record exact versions, parameters, and commands used

## Development Guidelines

### Data Management
```python
# Good: Clear data versioning and immutability
def load_raw_data(data_version="v1.0"):
    """Load raw sequencing data from specified version."""
    raw_path = Path(f"data/raw/{data_version}/sequences.fasta")
    if not raw_path.exists():
        raise FileNotFoundError(f"Data version {data_version} not found")
    return read_fasta(raw_path)

# Bad: Modifying data in place
def process_data(file_path):
    data = pd.read_csv(file_path)
    data.dropna(inplace=True)  # Never modify original data!
    data.to_csv(file_path)  # Never overwrite raw data!
---



## Config files and profiles
```
bash:iscc002:llm_configs 1068 $ tree profiles
profiles
├── bash_profiles
│   └── bashrc_iris_link -> /home/ahunos/.bashrc
├── databases
│   └── databases_config.yaml
├── programming_language_profiles
│   ├── python
│   │   └── matplotlib
│   │       └── matplotlib_defaults
│   └── R
├── software_configs
│   └── softwares_containers_config.yaml
└── workflow_profiles
    ├── executor_config.yaml
    ├── nextflow
    └── snakemakes
        ├── slurmConfig
        │   └── config.yaml
        └── slurmMinimal
            └── config.yaml

12 directories, 7 files
```

## Persistent Working Directories 
Scripts: ~/code/claude-scripts - Custom scripts and automation
Memory: ~/memories - Important information to remember (markdown)
Journal: ~/journal - Personal journal entries (markdown)
Ideas: ~/ideas - Creative ideas and thoughts (markdown)
To dos: ~/todos - Things to do, reminders, etc (markdown)
Projects: ~/projects - Active projects I'm working on (markdown)

## General Instructions & Projects
- You should search memories to see if there's an relevant information for my query, especially if you feel like you're missing context.
- Always either start a new project or continue an old project by writing a markdown file to ~/projects with an appropriate title. 
- create a directories using 'claude/scripts/init_project.py'
- As I do work, append important information to that file that you need to remember for the project.
- Do not use the following as variable names to avoid clashes with system variable names; [conditions, counts, results, sum, median, mean]
- In Genomic pipelines, Do not items like contig/chromosome names and sizes to ensure things don't break when we change codebase. Get contig names and sizes from the user supplied genome sizes file in the workflow.


### Visualization & Figures 
- Create 3 types of figues; png,pdf,svg for analysis place them under `png,pdf,svg` sub-directories.
- Figures should be of largest size possible
- Font type should always be Arial if font is available and of at least size 20. Headers should be Bold.
- Figure Axis should be legible, at least size 
- For multi-panel figures, the y-axis must be the fixed in order to standardize the comparison between groups ie. 3 multipanel boxplots comparing variables among groups should have fixed y-axis.
- prompt user to included appropriate statistical tests in figures. for example t-test with p-values when comparing groups

#### Figures for Nature magazine only
Use this for final figures when making manuscripts
- https://www.nature.com/nature/for-authors/formatting-guide
- Nature’s standard figure sizes are 90 mm (single column) and 180 mm (double column) and the full depth of the page is 170 mm.
- Use Arial or Helvetica font for all figures, with a size of 20pt when the figure is at final size (90mm or 180mm wide). 


## Statistical analysis
- Defaults 
    - p value = 0.05
    - adjusted p value = 0.05
    - multiple test hypothesis test = bonferoni
    

### genomic track visualization with IGV software
github here: https://github.com/sahuno/igver
```
singularity exec --bind /data1/greenbab /data1/greenbab/software/images/igver_latest.sif igver \
--input <DMSO_sample_1.bam DMSO_sample_2.bam | txt_file_with_paths_of_bams.txt> \
-r regions.txt \
-o "results_IGV_plots" \
--dpi 600 -d expand -p 1000 \
--genome 'mm10' --no-singularity && touch results_IGV_plots/done.txt
```
