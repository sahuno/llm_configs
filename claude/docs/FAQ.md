# Frequently Asked Questions

## Setup & Installation

### How do I launch Claude Code on the HPC?

Use the `sclaude` function defined in your `~/.bashrc`. It wraps `apptainer exec` with standard bind mounts and API key passthrough:

```bash
# Basic — opens Claude shell with standard mounts
sclaude

# With extra bind mounts for a specific project
sclaude /data1/greenbab/projects/my_project /data1/collab001/shared_data
```

Make sure your conda/mamba environment with Apptainer is active first (e.g., `mamba activate snakemake`).

### Why does `sclaude` use `apptainer exec` instead of `apptainer shell`?

`apptainer shell` does not source `~/.bashrc`, so aliases, API keys, and PATH customizations are lost. `sclaude` uses `apptainer exec /bin/bash --rcfile ~/.bashrc_container -i` to load a clean container-specific rc file that sets up everything correctly.

### What is `~/.bashrc_container` and why do I need it?

It is a lightweight shell rc file sourced inside Apptainer containers. It:
- **Unsets leaked RHEL functions** (`which`, `module`, `ml`, `_module_raw`) that break inside Debian-based containers
- **Cleans polluted env vars** (`LD_LIBRARY_PATH`, `CONDA_*`, `PYTHONPATH`, `MODULEPATH`, `LMOD_*`)
- **Sets container-first PATH** (`/opt/venv/bin`, `/opt/npm-global/bin` before host-mounted tools)
- **Exports API keys** safely using `${VAR:-}` pattern (no hardcoded secrets)
- **Sources `~/.bash_aliases`** for personal shortcuts

A copy lives in the repo at `claude/profiles/bash_profiles/bashrc_container`.

### How do I sync config changes from the repo to my local machine?

```bash
cp claude/CLAUDE.md ~/.claude/CLAUDE.md
cp claude/settings.json ~/.claude/settings.json
cp -r claude/hooks/*.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
cp -r claude/profiles ~/.claude/profiles
```

### Where are my API keys stored?

API keys are exported in `~/.bashrc` and passed into the container via `--env` flags in `sclaude()`. They are **never** committed to the repo. The `~/.bashrc_container` file references them with `export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"` — it inherits the value, it does not hardcode it.

---

## Hooks

### What are hooks and how do they work?

Hooks are shell scripts that Claude Code runs automatically before or after tool calls. They are defined in `settings.json` and live in `~/.claude/hooks/`. Each hook receives the tool input as JSON on stdin.

- **PreToolUse hooks** fire _before_ the action executes. Exit code 2 = BLOCK (prevents execution). Exit code 0 = allow.
- **PostToolUse hooks** fire _after_ the action executes. Exit code 0 with stderr output = WARN (show message but don't block).

### Which hooks are active?

| Hook | Event | Action | What it catches |
|------|-------|--------|----------------|
| `block-dangerous-commands.sh` | PreToolUse (Bash) | BLOCK | `rm -rf` on data dirs, `snakemake --reason` |
| `block-raw-data-writes.sh` | PreToolUse (Write/Edit) | BLOCK | Any write to `data/raw/` |
| `validate-reference-genome.sh` | PreToolUse (Bash, Write/Edit) | BLOCK | Cross-species mixing (mm10 + hg38), build mixing, chr naming mismatches |
| `enforce-genome-tag.sh` | PreToolUse (Bash, Write/Edit) | BLOCK | Genomic files (.bam, .bed, .vcf, etc.) without genome build tag in filename |
| `snakemake-dryrun.sh` | PostToolUse (Write/Edit) | WARN | Runs `snakemake -n` after `.smk` file edits |
| `block-hardcoded-contigs.sh` | PostToolUse (Write/Edit) | WARN | Hardcoded chromosome lists (e.g., `chr1, chr2, ...`) in scripts |
| `validate-yaml.sh` | PostToolUse (Write/Edit) | WARN | Invalid YAML syntax in config files |
| `warn-absolute-paths.sh` | PostToolUse (Write/Edit) | WARN | Hardcoded `/data1/` or `/home/` paths in .py, .R, .sh, .smk, .nf files |
| `log-slurm-submission.sh` | PostToolUse (SLURM MCP) | LOG | Logs every `slurm_submit_job` / `slurm_submit_batch` to `slurm_logs/claude_submissions.md` |

### Where are SLURM job submissions logged?

Every job submitted through the SLURM MCP server is automatically logged to `/data1/greenbab/users/ahunos/slurm_logs/claude_submissions.md`. The hook captures job ID, name, command, working directory, and timestamp. Dry runs are logged separately. The log path can be overridden via `SLURM_JOB_LOG` env var.

### A hook blocked something I actually want to do. How do I override it?

Hooks are safety rails, not walls. If a block is a false positive:
1. Tell Claude what you're doing and why the hook is wrong in this case.
2. Claude can adjust the command to satisfy the hook (e.g., add a genome tag to the filename).
3. If the hook is genuinely incorrect, edit the script in `~/.claude/hooks/` or temporarily remove it from `settings.json`.

### Why do hooks need `jq`?

All hooks parse their input as JSON (Claude Code passes tool parameters as JSON on stdin). Without `jq`, every hook silently fails and provides no protection. Make sure `jq` is installed in your container.

---

## CLAUDE.md Configuration

### What does CLAUDE.md do?

`CLAUDE.md` is the main instruction file that Claude Code reads at the start of every session. It contains:
- **Session initialization** protocol (project classification, directory scaffolding)
- **Universal rules** (data integrity, naming, logging, genome tagging)
- **Domain playbooks** (ONT methylation, RNA-seq, scRNA-seq, variant calling, Snakemake, AI/ML)
- **Environment reference** (SLURM resources, containers, reference genomes)
- **Figure standards** (fonts, sizes, 3-format output, colorblind palettes)
- **Quality gates** (pre-completion checklist)

### Where does CLAUDE.md live?

Two copies that must stay in sync:
- **Repo**: `claude/CLAUDE.md` — version-controlled, edit here first
- **Local**: `~/.claude/CLAUDE.md` — what Claude Code actually reads at runtime

After editing the repo copy, sync with `cp claude/CLAUDE.md ~/.claude/CLAUDE.md`.

### How does Claude Code find the profiles directory?

The `profiles/` directory is copied to `~/.claude/profiles/` alongside `CLAUDE.md`. Relative path references in `CLAUDE.md` (e.g., `profiles/databases/databases_config.yaml`) resolve from `~/.claude/`. If profiles are only in the repo, Claude Code won't find them.

### What happens at the start of every session?

Claude is instructed to:
1. Ask you to classify the session (domain, fresh vs continuation, objectives)
2. Read the relevant project file from `~/projects/` if continuing
3. Create a new project file if fresh
4. Search `~/memories/` for relevant context
5. Scaffold `data/raw/`, `data/processed/`, `src/`, `results/`, `figures/`, `workflows/`, `docs/` for analysis projects
6. Append progress to the project file as work proceeds

---

## Genomics Safety

### Why is genome build tagging mandatory?

Mixing genome builds (e.g., aligning to hg38 but calling variants against mm10 annotations) is one of the most common and hardest-to-detect errors in bioinformatics. The tagging rule forces every genomic output file to declare its build in both the filename and parent directory, making mismatches immediately visible.

**Pattern**: `data/processed/{genome_build}/{sample}.{genome_build}.{description}.{ext}`

Example: `data/processed/hg38/patient01.hg38.sorted.bam`

### Which file types need genome tags?

**Required**: `.bam`, `.cram`, `.bai`, `.bed`, `.bedgraph`, `.bedMethyl`, `.narrowPeak`, `.broadPeak`, `.vcf`, `.vcf.gz`, `.bcf`, `.bigwig`, `.bw`, `.bigbed`, `.gtf`, `.gff` (processed copies), count matrices.

**Exempt**: Raw data (`.fastq`, `.fq`, `.pod5`), figures, scripts, configs, logs, summary reports.

### What genome builds are supported?

Valid tags: `mm10`, `mm39`, `GRCm39`, `hg38`, `GRCh38`, `hg19`, `GRCh37`, `t2t`, `chm13`.

Reference paths (fasta, gtf, chrom.sizes, CpG islands) for each build are in `profiles/databases/databases_config.yaml`.

### How does the cross-species guard work?

The `validate-reference-genome.sh` hook checks every command and file write for genome references. If it sees both mouse (`mm10`, `mm39`) and human (`hg38`, `hg19`) references in the same operation, it BLOCKS immediately. This prevents accidental cross-species analysis.

---

## Logging

### What logging is required in scripts?

Every analysis script must produce a **timestamped log file** in `logs/{script_name}_{YYYYMMDD_HHMMSS}.log`. The log must capture:
1. Session header (timestamp, language version, args, library versions)
2. Data loading with dimensions (rows x columns)
3. **Every filter/data drop with before and after counts** — the most critical category
4. Merge/join dimensions and any lost rows
5. Sanity checks (sample order alignment, cross-validation)
6. Analysis milestones with `=== Section Name ===` markers
7. Output file confirmations with paths and dimensions
8. Warnings and errors
9. Session footer with total runtime and `sessionInfo()` / `pip freeze`
10. End-of-script marker: `=== DONE: {script_name} completed successfully ===`

### How do I set up logging in R?

```r
log_dir <- opt$log_dir
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
log_file <- file.path(log_dir, paste0("my_script_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".log"))
log_con <- file(log_file, open = "wt")
sink(log_con, type = "output", split = TRUE)
local({
  default_handler <- function(c) {
    cat(conditionMessage(c), file = stderr())
    cat(conditionMessage(c), file = log_con)
    invokeRestart("muffleMessage")
  }
  globalCallingHandlers(message = default_handler)
})
on.exit({ sink(type = "output"); close(log_con) }, add = TRUE)
```

### How do I set up logging in Python?

```python
import logging
from datetime import datetime

log_dir = args.log_dir
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"my_script_{datetime.now():%Y%m%d_%H%M%S}.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler(log_file)
sh = logging.StreamHandler()
fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
fh.setFormatter(fmt)
sh.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(sh)
```

### How do I know if a script ran to completion?

Check for the end-of-script marker as the last line of the log:
```
=== DONE: my_script.R completed successfully ===
```
If this line is absent, the run died mid-execution.

---

## Containers & HPC

### Why do `which` and `man` break inside the container?

RHEL/CentOS exports bash functions (from `/etc/profile.d/which2.sh` and lmod) that leak into Apptainer containers through the inherited environment. RHEL's `which()` function passes GNU flags that Debian's `/usr/bin/which` doesn't support. The `~/.bashrc_container` fixes this with `unset -f which module ml _module_raw`.

### What other RHEL-to-Debian collisions exist?

| Issue | Cause | Fix in `~/.bashrc_container` |
|-------|-------|------------------------------|
| `which` fails | Leaked RHEL bash function | `unset -f which` |
| `module: command not found` | Leaked lmod function | `unset -f module ml _module_raw` |
| Shared library errors | Host `LD_LIBRARY_PATH` pollution | `unset LD_LIBRARY_PATH` |
| Conda/mamba interference | Host `CONDA_*` vars | `unset CONDA_EXE CONDA_PREFIX ...` |
| Wrong Python picked up | Host `PYTHONPATH`/`PYTHONHOME` | `unset PYTHONPATH PYTHONHOME` |

### Why can't Claude run SLURM commands (`sbatch`, `squeue`, etc.) inside the container?

Apptainer inherits the host **environment** (all `SLURM_*` env vars are present), but **overlays the filesystem** — the container's `/usr/bin/` replaces the host's `/usr/bin/`, hiding SLURM binaries. The `sclaude()` function solves this by bind-mounting 5 components from the host:

| Component | Host Path | Container Path | Purpose |
|-----------|-----------|----------------|---------|
| Binaries | `/usr/bin/sbatch`, etc. | `/usr/local/bin/sbatch`, etc. | SLURM commands |
| SLURM libs | `/usr/lib64/libslurm.so*` | `/usr/lib64/libslurm.so*` | Shared libraries |
| Munge libs | `/usr/lib64/libmunge.so*` | `/usr/lib64/libmunge.so*` | Authentication library |
| Plugins | `/usr/lib64/slurm/` | `/usr/lib64/slurm/` | SLURM plugin modules |
| Config | `/etc/slurm/` | `/etc/slurm/` | Cluster configuration |
| Munge socket | `/run/munge/` | `/run/munge/` | Authentication socket |
| passwd/group | `~/.cache/claude/passwd_runtime`, `~/.cache/claude/group_runtime` | `/etc/passwd`, `/etc/group` | Synthetic files: host accounts + injected LDAP user entry (see below) |

**Why bind-mount instead of installing SLURM in the Dockerfile?** The cluster runs SLURM 25.05.3 (May 2025). Debian 12's apt repos have much older versions (~22.05). A protocol version mismatch between client and server causes silent failures. Bind-mounting the host's actual binaries guarantees version compatibility.

**Why binaries go to `/usr/local/bin/` not `/usr/bin/`**: We can't overlay individual files into `/usr/bin/` without disrupting the container's own binaries. `/usr/local/bin/` is already in the container PATH and has no conflicts.

**Why no `LD_LIBRARY_PATH` needed**: SLURM libs bind to `/usr/lib64/`, which is a default linker search path. Since the Debian container doesn't have `libslurm` or `libmunge` installed, there's no conflict.

### Why do GPU jobs fail silently on SLURM?

`--gres=gpu:N` can conflict with explicit `--mem` requests on some partitions. Try removing the `mem_mb` resource or use `--mem=0` (all available memory on the node).

### What containers are available?

All container paths are in `profiles/software_configs/softwares_containers_config.yaml`. Key ones:
- **Claude Code**: `claude_gemini_container_latest.sif`
- **ONT tools**: `onttools_v2.0.sif` (dorado + samtools), `sahuno/onttools:v3.0` (+ bedtools)
- **IGV**: `igver_latest.sif`

Always load paths from the config YAML — never hardcode container paths in scripts.

### Why must I set `APPTAINER_CACHEDIR`?

The default cache goes to `~/.apptainer/cache`, which counts against home directory quota on compute nodes. Set it to a project directory:
```bash
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
```

---

## Snakemake

### Why can't I use `snakemake --reason`?

There is no `--reason` argument in Snakemake. It doesn't exist. The `block-dangerous-commands.sh` hook blocks this to prevent confusing error messages. To see why rules will run, use `snakemake -n` (dry-run) which shows what would execute and why.

### My Snakemake rule uses a container but the command also calls `singularity exec`. What's wrong?

Double-container invocation. If a rule has a `singularity:` directive, the directive handles container execution automatically. Do NOT also wrap the shell command in `singularity exec -B ...`. Remove the `singularity exec` from the `shell:` block.

### How do I access config values in Snakemake?

With `--configfile`, values are accessed as `config["key"]`, not `config.key`. Python dict syntax, not attribute syntax.

### "No rule to produce" but my target is valid?

Check for whitespace in sample names or paths in the sample sheet. This is the most common cause. As a workaround, extract the failing step into a standalone shell script.

---

## Figures

### What formats are required?

Every figure must be saved in **3 formats**: PNG, PDF, and SVG, in separate subdirectories:
```
figures/
├── png/
├── pdf/
└── svg/
```

### What font and size should I use?

- **Font**: Arial (fallback: Helvetica, then sans-serif)
- **Minimum text size**: 20pt at final print size
- **ggplot2 trick**: For 20pt axis labels, set `base_size = 25` (because `axis.text` = `base_size × 0.8` = 20pt)

### What's the default color palette?

Okabe-Ito (colorblind-safe): `#0072B2` (blue), `#E69F00` (orange), `#D55E00` (vermillion), `#999999` (grey).

### When do I use Nature specifications?

Only when explicitly requested. Nature specs: single column = 90 mm, double column = 180 mm, full page depth = 170 mm, font = Arial/Helvetica 20pt.

---

## Project Management

### Where are project files stored?

`~/projects/<project-slug>.md` — one file per project. Contains objectives, decisions, key file paths, commands that worked, known issues, and next steps.

### What goes in a project file?

Every update must include:
1. What was done (specific, not vague)
2. Key file paths (absolute, copy-paste ready)
3. Commands that worked
4. Known issues / blockers
5. Exact next steps (numbered, actionable)

### What's the standard directory structure for analysis projects?

```
<project_root>/
├── data/inbox/         # Staging area — review before promoting to raw/
├── data/raw/           # IMMUTABLE — never write here after initial deposit
├── data/processed/
├── src/
├── results/
├── figures/{png,pdf,svg}/
├── workflows/{wf_snakemake,wf_nextflow}/
└── docs/
```

### What variable names are forbidden?

`conditions`, `counts`, `results`, `sum`, `median`, `mean` — these clash with R/Python builtins and cause subtle bugs.

---

## Troubleshooting

### Claude keeps hardcoding absolute paths in scripts. Why?

The `warn-absolute-paths.sh` hook catches this after the fact (PostToolUse), and `CLAUDE.md` instructs against it. If it persists, explicitly remind Claude: "use relative paths, not absolute."

### Claude mixed genome builds in a command. The hook didn't catch it?

The `validate-reference-genome.sh` hook checks the command text for co-occurring mouse and human references. If the references are in separate variables or config files that aren't visible in the command string, the hook may miss it. Always verify genome consistency manually for complex pipelines.

### Mamba gives `ImportError: cannot import name 'generate_parser'`

Conda/mamba version mismatch. Fix:
```bash
conda install -n base "mamba>=2.0"
export MAMBA_ROOT_PREFIX="$HOME/miniforge3"  # add to ~/.bashrc
```

### `FATAL: Couldn't determine user account information: user: unknown userid XXXXXXXXX`

**When it happens**: When any tool that calls `getpwuid()` — including `apptainer` itself — runs **from inside the Claude Code container** (i.e. after `sclaude()` has started). Claude Code's Bash tool triggers this when it runs `apptainer` or other system tools.

**Root cause**: Your UID (`164079095`) is an LDAP user. LDAP users are resolved via SSSD on the host but are NOT stored in the local `/etc/passwd`. Inside the Apptainer container, `nsswitch.conf` is `passwd: files` only (no SSSD). When any Go/C binary calls `getpwuid(164079095)`, NSS finds nothing and returns NULL → fatal error.

**Why intermittent**: SSSD caches lookups; cold-start or long-idle sessions may have cache misses even on the host, making the error seem random.

**Fix** (applied to `sclaude()` in `~/.bashrc`):
- Before launching the container, create `~/.cache/claude/passwd_runtime` and `~/.cache/claude/group_runtime`
- These are copies of the host `/etc/passwd`/`/etc/group` with one line appended for the current LDAP user
- Injected line format: `${USER}:x:$(id -u):$(id -g):${USER}:${HOME}:/bin/bash`
- These files are bind-mounted into the container at `/etc/passwd` and `/etc/group`
- Files live in `$HOME/.cache/claude/` (mode 700 dir, mode 600 files) — not `/tmp` — to prevent world-readable exposure and predictable-path attacks

**To verify the fix worked**:
```bash
# Inside the container
getent passwd $(id -u)   # should return your entry
apptainer --version      # should no longer fail
```

---

### `gh auth login` fails with `x509: certificate signed by unknown authority`

**When it happens**: When running `gh auth login` or any `gh` command inside the `sclaude()` container.

**Root cause**: `gh` is a Go binary. Go's TLS stack checks `SSL_CERT_FILE` then falls back to OS paths. The container's Debian/Ubuntu cert store only has public CAs — it's missing your institution's custom internal CA, which MSKCC uses for network TLS inspection.

**Fix** (applied to `sclaude()` in `~/.bashrc`):
- Detects the host CA bundle path (tries `/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem` → `/etc/ssl/certs/ca-bundle.crt` → `/etc/ssl/certs/ca-certificates.crt`, resolving symlinks via `readlink -f`)
- Bind-mounts the resolved bundle to `/etc/ssl/certs/ca-certificates.crt` inside the container
- Sets three env vars for complete tool coverage:

| Env var | Tool it covers |
|---|---|
| `SSL_CERT_FILE` | Go programs (`gh`, any Go HTTPS client) |
| `CURL_CA_BUNDLE` | curl-based tools |
| `GIT_SSL_CAINFO` | git HTTPS operations |

**To verify the fix worked**:
```bash
# Inside the container
gh auth login --with-token < ~/.tokens/githubToken.txt
gh auth status   # should show "Logged in to github.com"
```

---

### `grep` or `ripgrep` times out on a data directory

ONT data directories contain massive binary files (pod5, BAM, CRAM). Never run recursive text search on these. Use file-type filtering:
```bash
grep --include='*.py' --include='*.sh' -r "pattern" /path/
```
Or use `find` for filename searches. For comprehensive searches, write a standalone script.
