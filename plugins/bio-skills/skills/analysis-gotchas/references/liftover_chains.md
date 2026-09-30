---
tool: liftOver / chainSwap (UCSC kent)
version_observed: "unrecorded"
date: 2026-09-20
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  # a 0-byte chain lifts nothing and liftOver still exits 0
  [ -s "$CHAIN" ] || echo "empty chain file: $CHAIN"
---
# liftOver chain gotchas

## `chainSwap` does not give a valid reverse chain for repeat-family analyses

A UCSC `over.chain` is built from **nets**, which keep the best alignment per *target* base.
Netting is directional. `chainSwap` inverts coordinates but does **not** re-net, so wherever
many source loci map to one target locus — exactly the case for a high-copy repeat family —
the swapped chain systematically **under-lifts, and does so silently**.

Observed 2026-09-20 (RetroEvolution/mouseLINE1). Only `GCA_001624445.1ToMm10.over.chain.gz`
(CAST_EiJ → mm10, UCSC GenArk) exists; UCSC has **no** native mm10→CAST chain — not in
`goldenPath/mm10/liftOver/` (297 chains, zero mouse strains), not as a `vs*` dir, not in the
hub. Swapping it made every L1 subfamily look more "strain-specific", and **non-uniformly**
(L1MdF_III +18.9 pp vs L1MdTf_III +0.1 pp), which would distort a ranking rather than offset it.

### The control that catches it

Lift an **ancient** element set through the candidate chain and through a known-good chain for
a **more distant** relative. The ancient set must lift at least as well through the *closer*
relative's chain — otherwise the chain is bad.

    L1Lx9 (~20 Mya, 79.4% shared with rat -> present in every Mus strain)
      -> CAST  (diverged ~0.5 Mya) via swapped chain : 89.0%   <-- LOWER, impossible
      -> SPRET (diverged ~2-3 Mya) via native chain  : 90.6%

### Getting a real reverse chain

Build it natively: `lastz` → `axtChain` → `chainNet` → `netChainSubset`, with your genome as
target. Or skip liftOver and use structural-variant calls (e.g. Sanger MGP) for TE
presence/absence.

## A 0-byte chain file returns zero lifts silently

Which reads as "100% specific/absent". Guard with `[ -s "$CHAIN" ]`, not just `[ -f ]`.
A failed `wget` leaves exactly this.

## UCSC GenArk naming

Strain/assembly chains are named by accession, e.g.
`mm10ToGCA_001624865.1_SPRET_EiJ_v1.over.chain.gz`. A regex like `mm10To[A-Za-z0-9_]+\.over\.chain\.gz`
**silently excludes them** because of the `.` in the accession. Include `.` in the character
class when listing available chains.
