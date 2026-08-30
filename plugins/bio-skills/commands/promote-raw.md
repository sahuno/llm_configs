---
description: Promote staged data from data/inbox/ to the immutable data/raw/, with checksums and provenance
argument-hint: [files or glob — defaults to everything in data/inbox/]
---

Move reviewed data from `data/inbox/` into `data/raw/`, recording what it is and
where it came from. After this, `data/raw/` is immutable — the
`block-raw-data-writes` hook enforces it.

## Before moving

Ask, unless the answer is already recorded:

1. **Where did this come from?** Sequencing core and run ID, a collaborator, a
   public accession, a previous project. This is the field that is impossible to
   reconstruct later and the one always missing.
2. **What is it?** Assay, organism, genome build if already aligned, sample count.
3. **Has it been checked?** File count and sizes as expected, not truncated.

Refuse to promote data whose origin cannot be stated. Unprovenanced data in an
immutable directory is worse than data still in the inbox.

## Steps

```bash
# 1. checksums BEFORE the move, so corruption in transit is detectable
cd data/inbox && md5sum * > /tmp/inbox.md5

# 2. move
mv <files> ../raw/

# 3. verify the move did not corrupt anything
cd ../raw && md5sum -c /tmp/inbox.md5

# 4. record checksums alongside the data
md5sum <files> >> checksums.md5

# 5. make it read-only — belt and braces alongside the hook
chmod -w <files>
```

## Then write `data/raw/README.md`

Append an entry — do not overwrite:

```markdown
## <YYYY-MM-DD> — <short description>
- **Source**: <core / collaborator / accession, with run or order ID>
- **Assay**: <e.g. ONT WGS, 5mCG+5hmCG, R10.4.1>
- **Organism / build**: <mouse mm10 / human hg38 / unaligned>
- **Files**: <n> files, <total size>
- **Checksums**: recorded in `checksums.md5`
- **Notes**: <anything that will not be obvious in six months>
```

Report what moved, the checksum verification result, and the README entry.
