---
name: docker-hpc
description: |
  Use this skill when the user wants to build, create, or set up a Docker image
  for any scientific or bioinformatics tool — especially for HPC environments
  where Apptainer/Singularity will pull the result. Trigger for requests like:
  "dockerize X", "build a Docker image for Y", "containerize this tool",
  "I need a container for Z", "add this to my containers repo", or "push a
  Docker image to Docker Hub via GitHub Actions". This skill handles writing
  Dockerfiles, generating GitHub Actions CI workflows to build and push images
  without a local Docker daemon, and managing monorepo-style containers repos.
  Covers bioinformatics tools (samtools, STAR, CellRanger, dorado, modkit),
  R/Bioconductor packages (DESeq2, edgeR), conda/pip packages, and GPU/CUDA
  tools. Do NOT trigger for: writing Apptainer/Singularity .def files (use
  singularity-build skill), pulling existing images, or running containers
  interactively.
version: 1.0.0
author: Samuel Ahuno (ekwame001@gmail.com)
---

# Docker HPC Skill

Build principle-compliant Docker images for scientific computing on HPC and push
them to Docker Hub automatically via GitHub Actions. No Docker daemon needed on
the HPC — GitHub Actions does the build; Apptainer pulls the result.

## Bundled scripts

All scripts are in `scripts/` relative to this skill file.

| Script | Purpose |
|--------|---------|
| `scripts/preflight.sh` | Verify git, gh CLI, Docker Hub token, and username |
| `scripts/detect_context.sh` | Decide: standalone repo or add to existing monorepo |
| `scripts/generate_dockerfile.py` | Template engine → principle-compliant Dockerfile |
| `scripts/setup_repo.sh` | Create standalone GitHub repo + secret + push workflow |
| `scripts/add_to_monorepo.sh` | Add tool to existing `containers/self_made/` monorepo |

Templates live in `templates/` (Dockerfiles and GitHub Actions workflows).
Dockerfile principles are in `docs/dockerfile_principles.md`.

---

## Orchestration — follow these steps in order

### Step 1 — Run preflight

```bash
bash scripts/preflight.sh
```

Read the output carefully. If any check fails, stop and fix it with the user before
continuing. The script emits `DOCKER_USER=<username>` and `DOCKER_TOKEN=<varname>`
on success — capture these for use in later steps.

### Step 2 — Detect context (standalone vs monorepo)

```bash
bash scripts/detect_context.sh
```

Output is one of:
- `MODE=standalone` — no monorepo detected; create a new dedicated repo
- `MODE=monorepo REPO=<owner/repo>` — existing monorepo found; add to it

If monorepo mode, confirm the detected repo with the user before proceeding.

### Step 3 — Gather inputs from the user

Ask for:
1. **Tool name** — will become the Docker Hub image name (e.g. `samtools`, `dorado`)
2. **Tool version** — semver string (e.g. `1.21`, `1.4.0`)
3. **Tool type** — choose from: `ont | cuda | r | python-ml | biocli | generic`
   - Infer from tool name if obvious (dorado→ont, DESeq2→r, samtools→biocli)
   - Ask only if genuinely ambiguous
4. **Packages** — conda packages, pip packages, or "uses base image directly"
5. **Validation command** — how to confirm the install worked (e.g. `samtools --version`)
6. **Maintainer** — default to `gh auth status` username

### Step 4 — Generate the Dockerfile

```bash
python3 scripts/generate_dockerfile.py \
  --tool-name <name> \
  --tool-type <type> \
  --version <version> \
  --packages-conda "<space-separated>" \
  --packages-pip "<space-separated>" \
  --packages-r-bioc "<space-separated Bioconductor packages — r type only>" \
  --packages-r-cran "<space-separated CRAN packages — r type only>" \
  --validation-cmd "<cmd>" \
  --maintainer <maintainer>
```

For `r` tool type, always ask the user to separate packages into Bioconductor vs CRAN.
Pass Bioconductor packages (DESeq2, edgeR, limma, etc.) via `--packages-r-bioc`
and CRAN packages (ggplot2, dplyr, etc.) via `--packages-r-cran`.

The script prints the Dockerfile to stdout. Show it to the user for review.
**Do not proceed to Step 5 until the user approves the Dockerfile.**

If the tool type doesn't fit any template cleanly (truly exotic tool),
generate the Dockerfile using your knowledge of the 10 principles in
`docs/dockerfile_principles.md` rather than forcing a bad template match.

**Proprietary binary tools** (CellRanger, Guppy, GATK bundle, STARsolo, etc.)
are the most common exotic case. These are distributed as pre-built tarballs —
conda cannot install them. For these:
1. Use `ubuntu:22.04` or `condaforge/miniforge3` as base (not a tool-specific image)
2. Download the binary via `RUN curl` or instruct the user to `COPY` a local tarball
3. Use `ARG VERSION` so the Dockerfile is reusable across releases
4. Set `ENV PATH` to include the binary directory (principle 7)
5. Add `RUN <tool> --version` validation (principle 5)
6. If the download URL requires authentication, add a `--build-arg DOWNLOAD_URL` pattern
   and note that the user must supply a pre-signed/authenticated URL at build time
See principle 9 in `docs/dockerfile_principles.md` for a complete template.

### Step 5 — Set up the repo and CI

**Standalone mode:**
```bash
bash scripts/setup_repo.sh \
  --tool-name <name> \
  --version <version> \
  --dockerfile <path-to-approved-dockerfile> \
  --docker-user <DOCKER_USER> \
  --token-var <DOCKER_TOKEN>
```

**Monorepo mode:**
```bash
bash scripts/add_to_monorepo.sh \
  --repo <owner/repo> \
  --tool-name <name> \
  --version <version> \
  --dockerfile <path-to-approved-dockerfile> \
  --token-var <DOCKER_TOKEN>
```

### Step 6 — Tag and trigger the build

**Standalone:** `git tag v<version> && git push origin v<version>`
**Monorepo:** `git tag <tool>-v<version> && git push origin <tool>-v<version>`

### Step 7 — Monitor the build

```bash
gh run list --repo <owner/repo> --limit 3
gh run watch --repo <owner/repo>
```

Report the final image location:
`docker pull <docker-user>/<tool>:<version>`
`apptainer pull docker://<docker-user>/<tool>:<version>`

---

## Tool type → template mapping

| Tool type | Base image | Package manager | Template file |
|-----------|-----------|-----------------|---------------|
| `ont` | `nanoporetech/dorado` or `ubuntu:22.04` | mamba + pip | `ont_tools.Dockerfile` |
| `cuda` | `nvidia/cuda:12.4.1-base-ubuntu22.04` | mamba | `cuda_base.Dockerfile` |
| `r` | `bioconductor/bioconductor_docker:devel` | mamba + BiocManager | `r_base.Dockerfile` |
| `python-ml` | `condaforge/miniforge3` + CUDA | mamba + pip | `cuda_base.Dockerfile` |
| `biocli` | `condaforge/miniforge3` | mamba | `conda_base.Dockerfile` |
| `generic` | `condaforge/miniforge3` | mamba | `conda_base.Dockerfile` |

---

## Secret resolution (for reference)

The preflight script resolves the Docker Hub token in this order:
1. `DOCKERHUB_TOKEN` env var → use directly
2. `APPTAINER_DOCKER_PASSWORD` env var → reuse (warn user to verify write scope)
3. Neither set → instruct user to generate a token at `hub.docker.com → Account Settings → Security`

---

## Key guardrails

- Always show the generated Dockerfile to the user before any git operations
- Never `git push --force`
- Platform is always `linux/amd64` unless the user explicitly asks otherwise
- If preflight fails, stop and fix — do not work around missing prerequisites
- For Apptainer `.def` files, redirect the user to the `singularity-build` skill
