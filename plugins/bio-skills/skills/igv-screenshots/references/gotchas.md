---
tool: igver/modkit
version_observed: "0.6.1"
date: 2026-04-24
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  modkit bedmethyl tobigwig --help | grep -c chrom.sizes
---
## IGV / igver — gotchas for ONT methylation visualisation

### IGV with BAM (per-read methylation)

- **The old igver `--methylation` preset (before 2026-09-09) hung on large ONT BAMs**. It bundled `expand` display + `max-panel-height 1000` + `dpi 600`. As of 2026-09-09 `--methylation`/`--meth` is only an alias for `--color-by BASE_MODIFICATION` and no longer changes display/panel/dpi. Combined with 6 × ~100 GB modBaseCalls BAMs in one input list, IGV produces the first 1–2 snapshots in ~5 min and then sits idle indefinitely (observed: 45 min with 2/8 done, no progress, no error). The Java process is not crashed — it's stuck rendering thousands of expanded reads per region.
- **Working settings for large ONT BAMs (per-read view)**:
    - **2 representative BAMs** (one per group) instead of all replicates
    - `--overlap-display collapse`
    - `--max-panel-height 300`
    - `--dpi 300`
    - **Explicit** `--color-by BASE_MODIFICATION` instead of `--methylation` (the colour preset without the heavyweight expand/panel/dpi defaults)
    - With these settings: 8 regions complete in ~30 s
- **The per-read view is forensically useful but visually noisy.** Use it to confirm read support / check individual base-modification calls, not for cross-sample comparison. For comparison across replicates, use bigwigs (below).
- **IGV batch mode hangs forever on any error (modal dialog on Xvfb).** `BatchRunner.runWithDefaultGenome` clears the batch flag in its `finally` before the exception reaches `LongRunningTask`, which then calls `MessageUtils.showMessage` with the flag off and blocks on `JOptionPane`. Observed 2026-09-09: UCSC `hgdownload.soe.ucsc.edu` unreachable → `genome hg19` annotation fetch fails → three JVMs idle at 0% CPU for 10+ min with 0 snapshots. Symptom: java at ~160 MB RSS, `jstack` shows `MessageUtils.showMessage` / `invokeAndWaitOnEventThread`. Diagnose with `singularity exec <igver.sif> jstack <java pid>`. igver ≥ 2026-09-09 kills IGV after `--stall-timeout` seconds (default 600) with no new snapshot and retries only the missing regions; the underlying error is in `~/igv/igv0.log` (igver ≤ 1.2.3) or quoted in igver's error message from the kept `igver_igv_*` run dir (1.3.0). Also note IGV fetches RefSeq annotation from UCSC on every genome load, so a run needs outbound HTTPS even with cached genomes.

### Stale cached genome JSON → silent hang (confirmed 2026-09-25; fixed in igver 1.3.0)

- **Fixed in igver 1.3.0**: every IGV process runs with a fresh, run-scoped `--igvDirectory` (`igver_igv_*` under `$TMPDIR`) holding igver's own prefs and `DEFAULT_GENOME_KEY=<genome>`, so `~/igv` (cached genome JSONs, personal prefs, logs) is never read and genomes are fetched fresh from igv.org. On failure the run dir is kept and the error quotes its `igv0.log`. Extra prefs: `--igv-prefs FILE` (`KEY=VALUE` lines). The notes below apply to **igver ≤ 1.2.3** only.
- Other IGV 2.19.8 behaviours probed for 1.3.0: a 404 track URL and a dead-URL genome JSON block IGV on a dialog **without logging anything** (the log's last line names the resource); an unknown gene/contig or a start beyond the chromosome end silently **keeps the previous view** (whole genome only for the first region; exit 0, nothing logged — `goto` always returns OK), and a split view silently drops a bad locus — **igver 1.3.1 detects this** with a bare verification `snapshot` per region (IGV names it after the locus it shows) plus a `gotoimmediate All` reset, and exits 1 listing the regions; igver ≤ 1.3.0 saved the wrong view under the new name; index-older-than-BAM, corrupt BAM and unknown file types render without a dialog; `-g` on IGV's command line does not stop the default-genome load (`DEFAULT_GENOME_KEY` does); IGV copies `~/igv/prefs.properties` into a new `--igvDirectory` that has none.

- **Symptom**: igver produces 0 snapshots; `~/igv/igv0.log` (or `igv0.log.1` when `-j` > 1 — each JVM rotates to its own file) ends at `Loading genome: /home/<user>/igv/genomes/<genome>.json` with no error; `jstack` shows `JOptionPane.showMessageDialog`. The `--stall-timeout` retry hits the same dialog, so the job fails after 2 × timeout.
- **Cause**: IGV loads the genome from the cached `~/igv/genomes/<genome>.json` (bind-mounted home, not the image's `/opt/IGV_*/genomes`). Old cached JSONs point at retired Broad buckets that now return HTTP 403: `s3.amazonaws.com/igv.broadinstitute.org/...` (mm10, rn6) and `igv-genepattern-org.s3.amazonaws.com/...` (hg19, hg38). The error text never reaches the log.
- **Check**: `curl -s -o /dev/null -w '%{http_code}' -r 0-10 <fastaURL/indexURL/cytobandURL>` for each URL in the cached JSON; anything other than 200/206 is broken.
- **Also stale as of 2026-09-25**: the cached human hg38 JSON (fastaURL on igv-genepattern-org → 403); refreshed the same way and verified (BAM + BED render in 23 s).
- **BED tracks missing from snapshots (fixed in igver 1.2.3)**: a bare `squish`/`expand` batch command applies to every track. A squished or expanded annotation track (RefSeq, BED) fills the panel and pushes the BEDs below it out of view. With a BAM or without, and even at `-p 1000`. igver ≤ 1.2.2 emitted a bare `squish` by default; with those versions use `-d collapse`. 1.2.3 targets `<mode> <bam basename>` only. In your own `-c` batch commands, always name the track. BED files with a `#chr\tstart…` header line render fine.
- **Fix**: back up and replace with the current definition: `curl -sf https://igv.org/genomes/json/<genome>.json -o ~/igv/genomes/<genome>.json`. After the fix, mm10 (2 RNA BAMs × 8 regions, `-j 2`) finished in ~26 s.

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
