---
tool: process rule
version_observed: "n/a"
date: 2026-09-27
status: active   # active | fixed-upstream | superseded
detect_cmd: ""   # process rule, not tool-specific — nothing to probe
---
# verification_discipline.md — how to earn "done" and avoid false claims (process rule, all projects)

Learned the hard way in the RetroEM sessions of 2026-09-23 → 09-25 (project lessons log: `/data1/greenbab/users/ahunos/apps/RetroEM/docs/lessons/problemB_lessons.md`). Read before declaring any analysis, fix or benchmark complete.

## Definition of done
- **Full real data, not a slice.** A pilot, chromosome subset, subsample or simulation is a step, never the finish, when full real data exist. Done = the full samples ran end to end and passed their gates.
- **Every cited number has a committed script** and a run script/sbatch that produced it, with the command, commit, seed and input paths recorded (run manifest). Exploration one-liners must be turned into scripts before their numbers are cited.
- **Someone other than the builder checked it.** For anything non-trivial, a verifier (a separate agent or a second implementation) re-derives headline numbers from raw outputs.

## Before asserting a fault or a finding
- **Trace the whole data path** (e.g. model output → downstream table → correction step) before saying something "can't happen" or "is 100%". State the finding only at the strength the evidence supports.
- **Validate new metrics against an independent view** (IGV, a coverage plot, a second method) on a handful of cases before building on them. Read positions: use aligned blocks, not start/end midpoints (spliced reads jump over regions).
- **Look at an example before presenting it.** If the picture doesn't show the claim, suspect the metric.
- **Correct yourself in writing** as soon as a claim is disproved (docs, pages, ledger), and say what changed.

## Trust framework for benchmarks
- Pre-register metrics, decision rules and evaluation panels (git tag) before scoring; amend only with a dated reason, never after seeing that arm's result.
- Separate builder, verifier and adversary roles.
- Include known-answer canaries in every simulated run and a curated good/bad example panel for real data, frozen before evaluation.
- Metamorphic tests (invariances that must hold) and mutation tests of the scorer (planted errors it must catch).
- Red-team checklist of edge cases (strands, chromosome ends, empty inputs, multi-mapping, library types, resume paths, regression with new flags off).

## Engineering hygiene that prevented or caused past failures
- Fix root causes where they originate (e.g. strand from BED column 6, not a name suffix; missing tool added to the environment spec).
- Make pipeline steps idempotent; test resumption on purpose.
- Remove network dependencies from verification tools (local genome FASTA for IGV).
- Check external state (PR merged? branch deleted? credentials valid?) right before acting on it.
- When a safety hook blocks a legitimate command, put the command in a documented run script; don't weaken the hook.

## Added at the RetroEM Problem B P1 gate (2026-09-26)
- **Count reads with primary-only flags** (`samtools view -c -f 64 -F 2304` for pairs), never from idxstats / mapped-record totals: aligners like STAR write up to 100 records per multi-mapping read (a "117 M pairs" estimate was really 80.7 M).
- **Run a check before declaring it impossible.** A process that *can* vary (unseeded subsampling) may not have varied in the case at hand; a "non-reproducible" old run turned out byte-identical to a deterministic rerun. Escalate only after the cheap evidence is in.
- **A "no-op" claim for a flag needs the whole path to the reported number, per strand** (columns → EM → overlap/decoy table → correction), not just the component the flag touches.
- **Verify a likelihood term by brute-force enumeration of its support** against what it divides by; a column's total mass over all possible observations must be ≤ 1.
- **Probe determinism before promising byte identity**: run the same job twice (different nodes) before writing a byte-identical regression gate; set the sampling knobs that make it deterministic, and record them as fixed settings.
- **Pre-registration review pays**: four independent lens-reviewers (rules, simulator, implementation, completeness) found 83 issues in a first draft, including decision rules that could not adopt the fix they were meant to test and an arm that could win by shrinking every count. Have rules dry-run on a simple model before freezing them.

## Added at the RetroEM Problem B P4 gate (2026-09-26)
- **Integrity checks must read inputs and evidence, never the fit.** Three canary criteria written as "the model assigns X" (own passive > 0; count within bounds for a locus with an exact copy; "present in the results table") failed on correct pipelines. Check reference sequences against the genome and nonzero likelihood entries against the truth; report fitted assignments separately. For mixture models remember that nested or identical components absorb or split mass by design.
- **Test every new integrity check on a control where it must fail** (a plumbing fault, an arm without the feature) before trusting it; two of my replacement checks passed vacuously until a reviewer did this.
- **Positional selection rules need a uniqueness check**: "nearest a contig end" picked a locus duplicated on an unplaced contig.
- **Never edit a checkout while a test suite or pipeline runs against it**; run suites and coordinators from pinned worktrees.
- **An independent re-derivation is cheap relative to the claims it protects**: a verifier who never saw the scorer reproduced 5,060 of 5,060 benchmark numbers and the decision; write the comparison as a committed script.

## Added at the RetroEM Problem B P7 gate (2026-09-27)
- **Calibrate a simulator on the target data before pre-registering.** Measure fragment/read length, strandedness and depth of the real libraries and match them, or pre-register the difference as a limitation. A self-consistency gate ("insert within ± 5 bp of spec") does not test representativeness. (RetroEM: simulated 300 bp vs real ~150 bp fragments halved the boundary evidence the method relies on.)
- **A prediction and its observation must count the same thing.** Derive a prediction by pushing synthetic data through the same classifier that counts the observation (brute force), not by a separate formula; qualify every mechanism claim by the strata it was shown for; compare outcome-matched sets (loci selected for failing vs an unselected comparator is not a comparison).
- **Attribute a difference to each changed input.** When two configurations differ in more than one input (annotation and its overlap table), measure each separately before naming a cause; match cross-annotation loci by overlap, never by exact coordinates.
- **Red-team the report as a product.** Bound numbers are not enough: one adversary recomputes numbers from primary files, another checks every sentence against the data (overclaiming, missing qualifiers, definitions, missing limitations). Generate verdict words from data; after a core-code change re-run every regression the report cites; compute arm-independent quantities from their definition, not from files that exist only for reported rows.
- **Blinded image review:** pool several arms' lists so the reviewer cannot infer the arm; two independent reviewers + adjudicator; take every reviewer-visible label from an arm-neutral source; keep the key and arm-labelled logs outside the reviewer's directory; still expect proxies (e.g. a category that correlates with arm membership) and report them.
