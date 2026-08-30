---
tool: data.table::fread
version_observed: "1.14"
date: 2026-04-30
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  Rscript -e 'x<-data.table::fread(f,skip="chr"); stopifnot(is.numeric(x[[2]]))'
---
# data.table::fread quirks for BED-style files

## `skip = "chr"` does NOT skip a `#chr\tstart\t...` comment header
- **Symptom**: `fread(..., skip = "chr", header = FALSE)` reads the literal `#chr\tstart\t...` row as data, then downstream `as.integer(start)` returns NA and arithmetic on the column fails with `non-numeric argument to binary operator`. The error surfaces several lines after the actual misread.
- **Why**: `skip = "chr"` looks for the **first line containing the substring "chr"**. The comment header `#chr\tstart...` matches that pattern (the `#` doesn't disqualify it), so fread skips zero lines and reads the comment row as data. Confirmed 2026-04-30 on the SU2C EPDnew promoter BED in `scripts/29_fdr_genomewide.R`.
- **Fix**:
  ```r
  fread(path, skip = 1L, header = FALSE,
        col.names = c("chr","start","end","name","score","strand"),
        colClasses = c("character","integer","integer","character","character","character"))
  ```
  or, on data.table ≥ 1.14:
  ```r
  fread(path, comment.char = "#")
  ```
- **How to apply**: any BED-like input with a `#`-prefixed header (bedMethyl, modkit pileup output, EPDnew promoter BED, anything from UCSC `track`-headed exports). Always pass `colClasses` explicitly to catch the bug at read time, not three lines later when arithmetic blows up.

## Related: BED-like outputs in this lab use `#`-prefixed headers
- Per CLAUDE.md §"Genomic Output Conventions": all `.bed`, `.bedgraph`, `.bedMethyl` outputs we write start with `#chr\tstart\tend\t...` — a Python/R comment-friendly convention.
- This means **every fread of our own BED outputs needs the fix above** unless we use `comment.char = "#"`. Standardizing on the latter would prevent the recurrence.
