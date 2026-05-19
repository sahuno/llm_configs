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

### igver — overlay BED tracks get clipped when RefSeq Genes auto-expands

- **Default IGV behaviour gives `Refseq Genes` as much vertical space as it wants**. In gene-rich regions (e.g. Nova1 with ~20 transcript isoforms) the RefSeq panel grows tall enough to push any below-it tracks (BED overlays for DMRs/DMLs, custom annotation BEDs) below the PNG canvas. Symptom: 2 of 5 panels show your overlays, 3 of 5 don't, and the missing ones are always the panels with many isoforms — no error, just silent clipping. Confirmed 2026-05-15 on the QSTAT-CKi top-5 DMR validation snapshots.
- **`collapse Refseq Genes` in `--igv-config` is unreliable**: only fires when `maxPanelHeight N` is *also* set in the same batch config. With a setTrackHeight-only config (no `maxPanelHeight`), `collapse` is silently dropped. The dependency is empirical; not in the IGV batch docs.
- **`setTrackHeight` on RefSeq doesn't override its auto-expansion either** unless paired with `maxPanelHeight`. Same root cause.
- **Bottom line**: igver's PNG mode is brittle for multi-track layouts that include the always-on `Refseq Genes` track plus N custom BED overlays. For per-region DMR validation with overlay tracks, **use igv-reports instead** (next section). It gives interactive HTML with reliable track ordering and no canvas-clipping problem.

### igv-reports — slicing bigwig data is unsupported

- **`igv-reports` (`create_report`) cannot read bigwig directly.** `--tracks` and `--track-config` both route every input through a Python `reader.slice()` call. Dispatcher in `igv_reports/utils.py:getreader` only knows `bam | cram | vcf | bcf | wig`; `.bw` falls through `feature.infer_format` and raises `Exception: Unknown file format`. Setting `"format": "bigwig"` in `--track-config` JSON does NOT help — the JSON is for igv.js client config, not for the Python slicer. No `--standalone` toggle (or its absence) changes this; `slice()` is called either way.
- **Workaround that works**: pre-slice each bigwig to bedGraph over the report regions and pass the bedGraph files instead.
    ```bash
    # bedGraph per sample, sliced to the reporting windows (±flank)
    bigWigToBedGraph -chrom=$chr -start=$s -end=$e $sample.bw $tmp
    ```
    Then in `--track-config`: `{"name": "...", "url": "sample.top5.bedgraph", "type": "wig", "format": "bedgraph", "min": 0, "max": 100, "color": "..."}`. Confirmed 2026-05-15: 1.4 MB standalone HTML with 6 sample bedGraphs + 2 BED overlays + IGV.js embedded, fully offline.
- **Sites file**: a tab-delimited TSV with `--sequence`/`--begin`/`--end` column indices works as well as VCF, and lets you put informative columns (gene, |Δmeth|, nCG, areaStat) into the report's sortable table via `--info-columns`. With `--zero_based True` the BED-style coordinates pass through correctly.
- **When to reach for igv-reports over igver**: any time the deliverable is "let me click through these N regions and confirm support", the HTML report wins. igver is right when you need PNGs for a figure/manuscript; igv-reports is right for interactive validation. Layout is reliable in igv-reports because tracks come from JSON, not from IGV's auto-sizing logic.

### UCSC `bigWigToBedGraph` truncates `/dev/stdout` between calls

- **`bigWigToBedGraph <bw> <out>` opens `<out>` with `O_CREAT|O_WRONLY|O_TRUNC`**, even when `<out>` is `/dev/stdout`. Consequence: piping multiple invocations into a single append target *silently* loses everything but the last region:
    ```bash
    # WRONG — only the last region survives:
    for region in "${regions[@]}"; do
      bigWigToBedGraph -chrom=$c -start=$s -end=$e sample.bw /dev/stdout >> all.bg
    done
    ```
    Confirmed 2026-05-15: 5-region loop produced 168 rows (rows from the last region only) when each region individually produces 168-293. Fix: write per-region temp files and `cat >> all.bg` them.
    ```bash
    for region in "${regions[@]}"; do
      bigWigToBedGraph -chrom=$c -start=$s -end=$e sample.bw "$tmpdir/r$i.bg"
      cat "$tmpdir/r$i.bg" >> all.bg
      ((i++))
    done
    ```
- **General principle for any UCSC kent tool**: avoid `/dev/stdout` as the output argument for tools that take an output *path* (not a stream). Use a temp file, then concat. The same trick bites `bedGraphToBigWig`, `wigToBigWig`, etc.


### igver — silent exit-0 on render failure (agent + human hazard)

- **`igver` returns exit 0 even when it fails to produce PNGs**. Empirically confirmed 2026-05-18 across two install paths: stdout shows `[ERROR] Failed to generate all PNG files after 2 iterations.` and the `[INFO] Loaded N track(s)` banner — then exits 0 with an empty output dir. Any pipeline that gates on `subprocess.returncode != 0` (Snakemake `shell:` blocks, Nextflow processes, the `--also-png` path in `build_igvreports.py`) silently misses the failure. Humans skim the log, see "Exit 0", and assume success. **Always validate that expected PNG paths exist + are non-empty after igver returns**, regardless of the exit code. The expected-filename convention is `chr-start-end.<name>.<ext>` from BED row 4 (igver `_parse_bed_file` source).

- **conda-env install vs SIF install diverge invisibly**. Empirical 2026-05-18 against the same sites BED + tracks:
    - via SIF `/data1/greenbab/software/images/igver_latest.sif`: bedGraph + BAM both render correctly (`[SUCCESS]`, real PNGs). IGV Java binary is bundled at `/opt/IGV_2.19.5` inside the SIF.
    - via `pip install igver` (egg-link at `/data1/greenbab/users/ahunos/apps/igver`): both fail with `Failed to generate all PNG files after 2 iterations` because the underlying IGV Java binary is not on the env PATH. The conda env at `/home/ahunos/miniforge3/envs/snakemake/bin/igver` is the egg-link shim only; it cannot render without the SIF or a separately-installed IGV.
- **Recommendation**: for any agent-driven workflow (Snakemake/Nextflow rules, Claude `--also-png` pipelines, batch SLURM jobs), invoke igver via the SIF, not the conda binary. `apptainer exec --bind /data1/greenbab /data1/greenbab/software/images/igver_latest.sif igver ...` is the reliable path. The skill `--igver-cmd` flag (and `$IGVER_CMD` env var) exists in `build_igvreports.py` precisely to let pipelines pin the SIF invocation without hardcoding paths.
- **igver does handle bedGraph + BAM correctly when invoked via the SIF** — earlier docs caveats suggesting otherwise (bedGraph-only-works-with-bigwig) were over-cautious. The actual divergence between igv.js (used by igv-reports HTML) and IGV-desktop (used by igver) is one of *style* (lollipop vs heatmap) not *content*; both engines parse bedGraph fine.
