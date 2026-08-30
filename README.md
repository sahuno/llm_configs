# llm_configs

Claude Code plugins for computational biology — genomics skills, safety
guardrails, and HPC site configuration.

Maintained by Samuel Ahuno (Greenbaum Lab, MSKCC). Built for bioinformatics on a
SLURM cluster, but the skills and guardrails are usable anywhere.

## Install

```
/plugin marketplace add sahuno/llm_configs
/plugin install bio-skills@sahuno
```

Three plugins, install what you want:

| Plugin | Contents | Portable? |
|---|---|---|
| **bio-skills** | 13 skills, `/init-bio-project`, figure agent | Yes |
| **bio-guardrails** | 9 hooks — raw-data protection, genome-build tagging | Yes, if you adopt the layout |
| **hpc-site** | Genome + container registries, SLURM profiles, cluster knowledge | No — fork it |

`bio-skills` stands alone. `bio-guardrails` assumes the project layout that
`/init-bio-project` creates. `hpc-site` is one cluster's configuration, kept
public as a worked example of what a site layer holds — see its README for how
to stand one up elsewhere.

Installing merges into your Claude Code config. Nothing overwrites your
`settings.json`.

## Repository layout

```
.claude-plugin/marketplace.json   # marketplace manifest
plugins/
├── bio-skills/                   # skills/, commands/, agents/, scripts/
├── bio-guardrails/               # hooks/ + hooks.json
└── hpc-site/                     # profiles/, skills/, sites/
claude/                           # personal config, not shipped as a plugin
├── CLAUDE.md                     # author's memory file
├── settings.json                 # author's Claude Code settings
├── docs/, examples/, prompts/, mcps/
cli_coding_agents_setups/         # non-Claude agent setups (Gemini, Codex)
docs/
├── claude-code-on-hpc.md         # running under Apptainer on SLURM
├── skill-overlap-audit.md        # overlap with Claude Science skills
└── superpowers/                  # dated design records and plans
```

## Site and user profiles

Skills never hardcode genome or container paths. They read them from a
**profile**, and profiles come in two independent axes:

- **`sites/`** — cluster facts: reference genomes, container images, SLURM
  partitions, bind mounts. These change when you change institution.
- **`users/`** — person facts: plot defaults, sample-sheet conventions,
  `DO_NOT` rules. These follow you across institutions.

```bash
source plugins/hpc-site/profiles/resolve.sh
export SITE_PROFILE=mskcc-greenbaum   # or your own
export USER_PROFILE=$USER
profiles_export                       # -> $SITE_CONFIG, $USER_CONFIG
```

Both auto-select when there is exactly one real profile, and fail loudly rather
than guessing when ambiguous.

| File | Axis | Holds |
|---|---|---|
| `paths.yaml` | site | Roots, container cache, tool checkouts, bind-mount sets |
| `databases.yaml` | site | Reference genomes — fasta, gtf, chrom.sizes, CpG islands |
| `containers.yaml` | site | Container images |
| `executor.yaml` | site | SLURM partitions, scheduler defaults |
| `setup_preferences.yaml` | user | Sample-sheet format and analysis preferences |
| `DO_NOT.md` | user | Prohibited actions — read before anything destructive |
| `matplotlib_defaults`, `.Rprofile` | user | Plot defaults |

`profiles/sites/example/` and `profiles/users/example/` are fill-in templates.
Adding a new cluster means adding a profile, not forking the plugin.

## Running on HPC

If you run Claude Code inside an Apptainer container on a SLURM cluster, the
setup — the `sclaude` launcher, SLURM binary and library passthrough, and the
container-specific rc file — is in
**[docs/claude-code-on-hpc.md](docs/claude-code-on-hpc.md)**.

Not needed if you run Claude Code natively.

## Contributing a skill

Skills live in `plugins/bio-skills/skills/<name>/SKILL.md`. The filename is
case-sensitive on Linux — `skill.md` will not load. Keep site-specific paths out
of `SKILL.md`; read them from `$SITE_CONFIG` instead.


## Roadmap

The feature-request block that used to sit here has moved to where it can be
tracked and closed:

| Item | Status |
|---|---|
| Transition to Nextflow — resume, workflow metadata, Seqera AI | [#12](https://github.com/sahuno/llm_configs/issues/12) |
| Logging of tasks completed and pending | **Done** — `/wrapup` writes the five-field progress schema to `~/projects/<project>.md` |
| Use `uv` for Python package management | **Done** — `CLAUDE.md` §4 |

Open work is tracked in
[issues](https://github.com/sahuno/llm_configs/issues); the current
implementation plan is in
[`docs/superpowers/plans/`](docs/superpowers/plans/).
