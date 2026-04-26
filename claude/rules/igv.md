## IGV / igver — gotchas for ONT methylation visualisation

### IGV with BAM (per-read methylation)

- **CLAUDE.md §3E `--methylation` preset hangs on large ONT BAMs**. The preset sets `expand` display + `max-panel-height 1000` + `dpi 600`. Combined with 6 × ~100 GB modBaseCalls BAMs in one input list, IGV produces the first 1–2 snapshots in ~5 min and then sits idle indefinitely (observed: 45 min with 2/8 done, no progress, no error). The Java process is not crashed — it's stuck rendering thousands of expanded reads per region.
- **Working settings for large ONT BAMs (per-read view)**:
    - **2 representative BAMs** (one per group) instead of all replicates
    - `--overlap-display collapse`
    - `--max-panel-height 300`
    - `--dpi 300`
    - **Explicit** `--color-by BASE_MODIFICATION` instead of `--methylation` (the colour preset without the heavyweight expand/panel/dpi defaults)
    - With these settings: 8 regions complete in ~30 s
- **The per-read view is forensically useful but visually noisy.** Use it to confirm read support / check individual base-modification calls, not for cross-sample comparison. For comparison across replicates, use bigwigs (below).

### IGV with bigwig (per-CpG methylation fraction)

- **Bigwigs are ~3 orders of magnitude lighter than BAMs** (~165 MB vs ~100 GB per sample) — IGV startup dominates the runtime, rendering is near-free.
- **All replicates can be displayed in one figure** without IGV strain. 6 ONT methylation bigwigs render at DPI 600 in 27 s for 8 regions.
- **Modkit's `bedmethyl tobigwig` emits percent (0–100), not fraction (0–1).** Track values can reach 100. Set y-axis to `0,100` for direct interpretation; `0,1` would clip everything to the top.
- **IGV autoscales each track independently by default** — visually similar bars across tracks can hide actual range differences (we observed y-ranges of 82, 87, 95, 100 across replicates of the same DMR). For cross-sample comparison this is misleading.
- **Fix with `igver --igv-config <file>`** containing IGV batch commands. A single-line file with `setDataRange 0,100` (no track name → applies to all loaded tracks) is injected before each `snapshot` and fixes every track to the same y-axis. Confirmed 2026-04-24.
- **The `-c` flag injects RAW IGV batch syntax**, not Java property KEY=VALUE. Use commands like `setDataRange 0,100`, `colorBy BASE_MODIFICATION`, `viewaspairs` — see https://igv.org/doc/desktop/#UserGuide/tools/batch/.

### Generating methylation bigwigs from modkit bedMethyl

- **`modkit bedmethyl tobigwig` errors on contigs absent from chrom.sizes.** Symptom: a Rust panic `thread 'tokio-runtime-worker' panicked ... Couldn't send section.: SendError(..)` followed by the actual error `Input bedGraph contains chromosome that isn't in the input chrom sizes: <contig>`. The Rust panic is the worker dying because the main loop already returned an error — the chromosome mismatch is the real problem.
- **Raw modkit pileup bedMethyl includes non-canonical contigs** (e.g. mm10's `chr*_*_random`, `chrUn_*`). The 22-contig "canonical" sizes file commonly used elsewhere in our pipelines (`mm10.sorted.standard.chrom.sizes`) trips this error.
- **Two fixes**:
    1. **Recommended**: derive a full chrom.sizes from the FASTA index: `awk -v OFS='\t' '{print $1, $2}' <ref>.fa.fai > full.chrom.sizes`. mm10 → 66 contigs; covers everything modkit can emit.
    2. Pre-filter bedMethyl to canonical contigs before piping into modkit. More work, only useful if you specifically don't want non-canonical bigwig data.
- **The nf-core module `modkit/bedmethyltobigwig`** wraps this command cleanly; it accepts gzipped bedMethyl. Containerised via `ont-modkit:0.6.1` biocontainer. Module path in nf-core/modules: `modules/nf-core/modkit/bedmethyltobigwig/`.

### Submitting igver via SLURM (MSKCC HPC)

- **Resource sizing**:
    - BAM mode (large ONT BAMs): 4 cpu / 16-24 GB / 1 h is sufficient for 8 regions × 2 BAMs at the lighter settings above.
    - Bigwig mode: 4 cpu / 16 GB / 1 h is generous; actual usage is ~1 cpu / 1 GB / 30 s.
- **Bind paths** must cover both the data location and the project location. For our setup: `apptainer exec --bind /data1/greenbab --bind /data1/greenbab/projects` covers most cases.
- **`--no-singularity`** is mandatory when running igver inside an apptainer SIF that already vendors IGV — otherwise igver tries to nest containers.
