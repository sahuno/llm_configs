# Hooks Implementation Plan

Date: 2026-03-03
Status: Decisions finalized — ready to implement when CLAUDE.md.dev is promoted
Reference: hooks_suggestions.md, CLAUDE.md.dev

---

## Decisions (2026-03-03)

| Decision | Answer |
|----------|--------|
| Scope | Project-level `.claude/settings.json` in this repo (shared). Promote to `~/.claude/settings.json` later. |
| Hook 1 skip list | Skip `llm_configs/` only, warn everywhere else |
| Hook 2 notification | Brief `systemMessage` (~20 tokens) — option B |
| Hook 3 (genome tag) | **ALREADY IMPLEMENTED** in `~/.claude/settings.json` as `enforce-genome-tag.sh` (PreToolUse on Bash + Write\|Edit). Not needed here. |
| Deploy timing | Wait for CLAUDE.md.dev to be promoted to live CLAUDE.md |

## Existing user-level hooks (already in ~/.claude/settings.json)

For reference — these are already running on every session:

| Hook | Event | Matcher | What it does |
|------|-------|---------|---|
| `block-dangerous-commands.sh` | PreToolUse | Bash | Blocks destructive commands |
| `validate-reference-genome.sh` | PreToolUse | Bash, Write\|Edit | Validates genome ref paths |
| `enforce-genome-tag.sh` | PreToolUse | Bash, Write\|Edit | Enforces genome build tags in filenames |
| `block-raw-data-writes.sh` | PreToolUse | Write\|Edit | Prevents writes to data/raw/ |
| `snakemake-dryrun.sh` | PostToolUse | Write\|Edit | Auto dry-run after Snakefile edits |
| `block-hardcoded-contigs.sh` | PostToolUse | Write\|Edit | Warns on hardcoded chr names/sizes |
| `validate-yaml.sh` | PostToolUse | Write\|Edit | Validates YAML syntax |
| `warn-absolute-paths.sh` | PostToolUse | Write\|Edit | Warns on hardcoded absolute paths |
| `log-slurm-submission.sh` | PostToolUse | mcp slurm submit | Logs SLURM job submissions |

**Conclusion**: Hooks 1 and 2 below fill gaps that the existing hooks don't cover (project scaffold detection and results dir structure enforcement).

---

## Architecture

```
.claude/
├── settings.json              # hook registrations (committed, shared)
├── settings.local.json        # permissions (gitignored, per-machine)
└── hooks/
    ├── check_project_scaffold.sh    # Hook 1: session-start scaffold check
    └── ensure_results_figures.sh    # Hook 2: auto-create figures dirs
```

---

## Hook 1: Auto-scaffold check on session start

**Event**: `UserPromptSubmit` (no matcher — fires on every prompt)
**Behavior**: `once: true` — fires on first prompt only. Warn if no project structure detected. Non-blocking.
**Skip**: Directories containing `llm_configs` in the path.
**Performance**: ~5ms (two `test -e` checks).
**Context cost**: ~40 tokens, once per session.

### settings.json entry

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check_project_scaffold.sh",
          "timeout": 5,
          "once": true,
          "statusMessage": "Checking project structure..."
        }
      ]
    }
  ]
}
```

### Script: `.claude/hooks/check_project_scaffold.sh`

```bash
#!/bin/bash
# Hook 1: Check if project scaffold exists
# Event: UserPromptSubmit (once: true — first prompt only)
# Behavior: Non-blocking warning
# Author: Samuel Ahuno
# Date: 2026-03-03

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')

# Skip: llm_configs repo is a config repo, not an analysis project
if [[ "$CWD" == *"llm_configs"* ]]; then
    exit 0
fi

# Check for project scaffold indicators
HAS_CONFIG=false
HAS_DATA=false

[[ -f "$CWD/config.yaml" ]] && HAS_CONFIG=true
[[ -d "$CWD/data" ]] && HAS_DATA=true

# If both missing, this is likely an uninitialized project directory
if [[ "$HAS_CONFIG" == "false" && "$HAS_DATA" == "false" ]]; then
    jq -n '{
        "systemMessage": "No project structure detected in this directory. Consider running: python /data1/greenbab/users/ahunos/apps/llm_configs/claude/scripts/init_project.py --type <analysis|pipeline|ml> --genome <build>"
    }'
    exit 0
fi

exit 0
```

---

## Hook 2: Auto-create figures dirs in results

**Event**: `PostToolUse` with matcher `Bash`
**Behavior**: After any Bash command mentioning `results/`, check if run dirs under `results/` have `figures/{png,pdf,svg}`. Create them if missing. Brief notification.
**Performance**: ~10ms (shallow `for` loop on `results/*/`).
**Context cost**: ~20 tokens, only when dirs are actually created (silent otherwise).

### settings.json entry

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ensure_results_figures.sh",
          "timeout": 10
        }
      ]
    }
  ]
}
```

### Script: `.claude/hooks/ensure_results_figures.sh`

```bash
#!/bin/bash
# Hook 2: Ensure results dirs have figures/{png,pdf,svg} subdirs
# Event: PostToolUse (Bash)
# Behavior: Non-blocking, auto-fix with brief notification
# Author: Samuel Ahuno
# Date: 2026-03-03

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Quick filter: only act if the command mentioned results/
if ! echo "$COMMAND" | grep -q 'results/\|results '; then
    exit 0
fi

RESULTS_DIR="$CWD/results"

# No results dir yet — nothing to do
[[ -d "$RESULTS_DIR" ]] || exit 0

# Find run dirs (one level deep, starting with digits = date prefix)
CREATED_DIRS=false
for run_dir in "$RESULTS_DIR"/[0-9]*; do
    [[ -d "$run_dir" ]] || continue

    for fmt in png pdf svg; do
        if [[ ! -d "$run_dir/figures/$fmt" ]]; then
            mkdir -p "$run_dir/figures/$fmt"
            CREATED_DIRS=true
        fi
    done
done

if [[ "$CREATED_DIRS" == "true" ]]; then
    jq -n '{
        "systemMessage": "Auto-created missing figures/{png,pdf,svg} subdirectories in results/."
    }'
fi

exit 0
```

---

## Combined project-level settings.json

This merges with the existing `permissions` block in `.claude/settings.local.json`.
Note: hooks go in `.claude/settings.json` (committed), permissions stay in `.claude/settings.local.json` (gitignored).

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check_project_scaffold.sh",
            "timeout": 5,
            "once": true,
            "statusMessage": "Checking project structure..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ensure_results_figures.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

---

## Rollout plan

1. Wait for CLAUDE.md.dev to be promoted to live CLAUDE.md
2. Create `.claude/hooks/` directory with both scripts
3. `chmod +x` both scripts
4. Add hooks block to `.claude/settings.json`
5. Test: open a new Claude session in a bare directory — Hook 1 should warn
6. Test: run `mkdir -p results/20260303_test` — Hook 2 should create figures subdirs
7. Once confirmed working, copy hook entries into `~/.claude/settings.json` for all projects

---

## Future: promote to user-level

When ready, add these entries to the existing `~/.claude/settings.json` hooks alongside the current `PreToolUse` and `PostToolUse` blocks. The hook scripts can stay in this repo (referenced by absolute path) or be copied to `~/.claude/hooks/`.
