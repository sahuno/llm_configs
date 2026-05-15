# sciAuditor — ROADMAP

Open work items ordered by load-bearing-ness. Pick from this list at
the start of each round.

## Near-term (would land in 1-2 rounds each)

### 1. Casetrack manifest integration
The schema v0.2 was designed to map onto a real manifest format
later. Now that the inference half is solid, do the manifest pass:
- Read the casetrack manifest schema (https://github.com/sahuno/casetrack)
- Define how `inputs[]` / `outputs[]` / `dataframes[]` / `models[]`
  in the auditor's YAML correspond to manifest entries
- Add a `--manifest <path>` flag to the aggregator that loads the
  expected contract and diffs against the inferred YAML
- Each divergence becomes a finding (severity TBD per delta type)

### 2. Layer B runtime trace
Static analysis is fundamentally limited. Layer B actually executes
a script on head-of-real (first N rows) data and ground-truths:
- dynamic path resolution (when paths come from `$env`, `paste0()`,
  loop iterators)
- filter row counts (before/after each `dplyr::filter` / `df.query`)
- library-internal I/O (e.g. `DESeqDataSetFromMatrix` reading
  metadata from somewhere)
- runtime values for `set.seed(varname)` cases
Requires per-script `audit_fixture:` override in the manifest for
balance-sensitive scripts (DE analysis, paired tests).

### 3. Snakemake / Nextflow DAG audit
The cross-script audit deferred in `01_first_principles_brainstorm.md`
§12.5. Auditor reads a Snakefile / nextflow main.nf, builds the rule
DAG, and validates:
- script A's `output:` files match script B's `input:` files in
  schema (use the inferred YAML schemas from per-script audits)
- intermediate files have a genome tag
- shared params don't drift across rules

### 4. Workflow-DAG awareness inside the cohort aggregator
Less ambitious than full Snakemake parsing — given a numbered
script set (02_*, 03_*, etc.), infer the execution order from
filename prefixes + each script's `inputs[]`/`outputs[]` and
display a DAG view alongside the per-script table.

## Medium-term

### 5. Layer C LLM assist
Narrow scope: "what does this script do scientifically" semantic
summary as a separate `scientific_intent:` block in the YAML.
Useful as audit context, not as ground truth. Guard with: every
LLM claim is cross-checked against Layer A or B; any LLM claim
contradicted by static evidence is dropped.

### 6. `claude /audit` slash command
Wrap the aggregator as a Claude Code skill. `/audit <path>` runs
the parser, parses the report, and surfaces findings inline in the
Claude Code conversation. Slash-command surface design in
`02_inference_design.md` §8 Q4.

### 7. Pre-commit hook integration
Git hook that runs sciauditor on changed scripts and blocks the
commit on `BLOCKER` findings unless `--no-verify` is set (with an
explicit log entry of who bypassed the gate and why).

## Smaller polish items

### 8. Deep-chain Python lineage
Patterns like `clinical.drop_duplicates(...).set_index(...)["col"]`
where the outer Subscript wraps a Call chain. Currently misses
~2-3 such bindings per ~500-line Python script. Walk the Subscript
base through Call nodes to recover.

### 9. R `pair_unit` from launcher-only entry
Today's pair detection: parser_r runs `--pair_launcher <bash>`.
Alternative: pass `--pair_analysis <R>` to parser_bash and let bash
parser drive the pair composition when the launcher is the starting
point of interest. Symmetry; same shape of `pair_unit` output.

### 10. Python `pair_unit` support
parser_py doesn't support `--pair_launcher` yet (only R does).
Lab Python scripts that are launched by bash (e.g. snakemake rules)
would benefit. Mirror parser_r's logic in parser_py.

### 11. `transformations[]` predicate extraction with row counts
Currently `dataframes[].transform.predicate` holds the deparsed
filter text; the rows-before/after fields stay null until Layer B
runs. Could populate from runtime trace.

### 12. `figures[]` first-class
Today `ggsave` / `savefig` lands in `outputs[]`. Promote them into
their own array with `derived_from: <contrast_id>` so the audit can
answer "which contrast does this volcano show?".

### 13. `functions_defined[]` + helper-I/O propagation
Two-pass walk so a `save_figure_3fmt()` call's three ggsave outputs
appear in `outputs[]` with call-site attribution (not definition-
site). Big visual win on the DESeq2 fixture (collapses ~29 outputs
into ~10 logical figure groups).

### 14. parser_bash getopts surface
The current bash parser handles simple `VAR=value` assignments but
doesn't model `getopts` argument parsing (in `03_run_one.sh` style
benchmark wrappers). Add a `config_interface.framework: getopts`
flavor with `flag` / `long_name` / `default` extraction.

### 15. Multi-script grade weighting
Cohort headline currently treats each compliance check equal-weight.
BLOCKERs should weight more than NOTEs. Re-derive the project-wide
grade so a BLOCKER drags it harder than a NOTE.

## Out of scope (for now)

- Tooling outside R/Python/bash (Julia, MATLAB, Snakemake DSL parsed
  natively, Nextflow Groovy)
- Real-time IDE integration (VSCode extension, RStudio addin)
- Auto-fix suggestions ("change `header=FALSE` to `header=TRUE`")
- Web UI for the cohort report
