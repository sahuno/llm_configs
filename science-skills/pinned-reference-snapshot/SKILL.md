---
name: pinned-reference-snapshot
description: Pin an external reference resource to a vendored, checksummed snapshot so an analysis cannot silently change under a database release. Use whenever an analysis path calls out to a versioned external resource — MSigDB or msigdbr gene sets, a GO or Reactome release, an Ensembl or RefSeq annotation build, a repeat or TE consensus library, a pathway or drug-target table — and especially when numbers moved between reruns of unchanged code, when a reviewer asks which release was used, when methods text must state a version, or when someone proposes calling the resource API live inside a script. Covers vendoring the snapshot, the manifest schema, verifying the checksum at load, and the change ledger that records what moved when the pin is bumped. Ships helpers sha256_file, write_pin_manifest, verify_pin and change_ledger.
---

# Pinned reference snapshot

A live call to a reference database inside an analysis path makes the resource
version an invisible input. The code is unchanged, the seed is fixed, the data
is fixed — and the enrichment result moves, because the collection gained 200
sets last Tuesday. Nothing in the script records which version produced which
number, so the discrepancy is unattributable after the fact and the methods
section cannot be written truthfully.

Pinning converts that hidden input into a declared one.

## What counts as a reference resource

Anything fetched by name rather than by content hash, and maintained by someone
else on their own release schedule: gene-set collections, ontology releases,
genome and transcriptome annotation builds, repeat and TE consensus libraries,
pathway databases, ID-mapping tables, drug-target and variant catalogues.

Not a reference resource: your own upstream outputs (those are lineage, not
pinning) and constants you can write down.

## Step 1 — vendor, once, in its own step

Fetch the resource in a dedicated cell or script that does nothing else, and
write it to a plain interchange format next to the analysis — GMT for gene sets,
TSV or GTF for tables and annotations. The fetch is the only place the network
is touched. Keep the fetch code: it is the record of *how* the snapshot was
obtained, and it never runs again unless the pin is bumped deliberately.

## Step 2 — write a manifest beside it

`write_pin_manifest(entries)` emits one row per vendored file:

| column | why it is there |
|---|---|
| `file` | the vendored filename |
| `source` | the exact query, not the database name — `msigdbr:C5:GO:BP`, not `MSigDB`. Collection, subcategory and filters included, because that is what you would have to retype to reproduce it |
| `n_records` and any domain counts | e.g. sets and gene-set pairs. These are what you check first when a pin moves |
| `sha256` | content identity; the only field that detects silent corruption or a hand-edit |
| `resource_version` | the upstream release, verbatim as the provider states it |
| `exported_utc` | when you took the snapshot |

Add domain columns freely — `write_pin_manifest` passes extra keys through. The
six above are the ones that answer the questions actually asked of a methods
section.

## Step 3 — the analysis path reads the snapshot, never the API

Two rules, both load-bearing:

- No analysis script imports the resource client. If the code that computes a
  result can reach the network, the pin is decorative.
- The loader calls `verify_pin(manifest_path)` and stops on a checksum
  mismatch. Without that, "we pinned it" is an assertion about a file nobody
  re-read. This costs milliseconds and is the difference between a pin and a
  comment claiming there is a pin.

## Step 4 — when the pin moves, re-derive and write a change ledger

Bumping the pin is not a version-number edit. Every downstream number derived
from the resource must be recomputed, and the difference recorded — otherwise
the manuscript mixes numbers from two releases and no one can tell which.

`change_ledger(old, new, key_cols, value_cols, call_col=...)` produces one row
per unit with `<col>_old`, `<col>_new`, `<col>_delta`, and a `change` verdict
from a deliberately small vocabulary:

- `NEW (absent before)` — the unit did not exist under the old pin
- `DISAPPEARED` — it no longer exists
- `call GAINED` / `call LOST` — it crossed the significance threshold
- `moved, call unchanged` — values shifted, the conclusion did not
- `identical`

Report the counts of that vocabulary. "Results were similar" is not a finding;
"1,341 moved without changing the call, 61 gained, 11 lost, 9 new, 9 gone" is
one, and it is the sentence a reviewer needs. The gained/lost rows are the only
ones that can alter a claim in the paper — check every one of them against the
text.

## Step 5 — say it once, in one place

State the pin in exactly one location — the manifest is the source, the methods
text quotes it. Methods prose that describes the pinning as done, in a document
whose other paragraph still describes a live call, is a common and expensive
failure: it survives revisions because each paragraph looks correct in
isolation. When you touch the pin, re-read the whole methods section, not the
paragraph you edited.

## Pitfalls

- **Filtering after loading is part of the pin.** A minimum set size or a
  gene-universe restriction applied downstream changes the effective collection.
  Record the filter in `source` or as a manifest column, or the counts will not
  reproduce.
- **The provider's version string is not always the release date.** Record both
  when they differ; a package version and the underlying database release are
  different facts.
- **Do not re-export the snapshot to "clean it up".** Any rewrite invalidates the
  checksum and makes the pin unverifiable against the provider.
- **A snapshot is not a checkpoint.** Vendored reference files are small and
  belong beside the code; do not route them through large working-data storage.
