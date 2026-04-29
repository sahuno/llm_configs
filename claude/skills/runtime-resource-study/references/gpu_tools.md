# GPU tools — what changes when the workload runs on a GPU

The CPU-oriented stages still apply (preflight, stage-gated design, model fit,
validation), but the factor menu, monitoring, hardware controls, and SLURM
mechanics all shift. Read this whole file before designing the study for any
GPU-bound tool (basecaller, GPU-accelerated aligner, GPU-accelerated variant
caller, etc.).

## 1. Decide it's a GPU tool

Trigger this reference when the user mentions any of:

- **Basecallers**: dorado, guppy, bonito, ont-basecaller
- **GPU-accelerated aligners**: Parabricks fq2bam, minimap2-with-CUDA-prefilter
- **GPU-accelerated variant callers**: DeepVariant, DeepSomatic, Clair3 (GPU mode),
  Parabricks haplotypecaller
- **Generic GPU compute**: CUDA / cuDNN / pytorch / tensorflow inference
- Any job that requires `--gres=gpu:N` to run

If unsure, ask. The wrong runner will produce a study that "works" but mismeasures
GPU memory and utilisation.

## 2. Different factor menu

### dorado basecaller

| Factor | Levels | Why it matters |
|---|---|---|
| **Model size** | `fast`, `hac`, `sup` | 10-50x speed/accuracy trade-off — dominates everything else. Don't skip this factor. |
| **Mod-base calls** | `none`, `5mCG_5hmCG@latest`, `5mCG_5hmCG@latest,6mA@latest` | Each enabled head adds ~30-50 % wall |
| **GPU model** | A100, L40S, H100, V100 | 3-10x perf delta across vintages — pin via `--gres=gpu:<type>:1` |
| **GPU count** | 1, 2, 4 (`--device cuda:0` vs `cuda:all`) | Sub-linear scaling; often diminishing past 2 |
| **Batch size** | `--batchsize 64, 256, 1024` | GPU-RAM bound; OOM is the failure mode (silent on some kernels) |
| **Runners/device** | `--num-runners-per-device 1, 2, 4` | Hides host-GPU transfer latency |
| **CPU threads** | 8, 16, 32 | For pre/post-processing pipeline (file I/O, header parsing) |
| **Output emission** | `--emit-fastq`, `--emit-sam`, `--emit-moves` | Bytes-per-sample on output side |

### GPU-accelerated aligners (Parabricks fq2bam, minimap2-CUDA)

| Factor | Levels | Why it matters |
|---|---|---|
| GPU count | 1, 2, 4, 8 | Aligners scale better than basecallers |
| GPU model | A100, H100 | Tensor-core support varies |
| Batch size / chunk size | tool-specific | Often the biggest knob after GPU count |
| Index in GPU memory | yes / streamed | Massively affects wall on first read |
| Number of streams | 1, 2, 4 | CUDA stream concurrency |
| CPU threads | 8, 16, 32 | For BAM I/O |

### GPU-accelerated variant callers (DeepVariant, Clair3 GPU)

| Factor | Levels | Why it matters |
|---|---|---|
| Model checkpoint | wgs, wes, ont, hybrid | Different graph sizes |
| Shards | 1, 4, 16, 64 | DeepVariant's `--num_shards` |
| GPU count | 1, 2, 4 | One model per GPU |
| Region size | 1Mb, 10Mb, full chr | Memory vs scheduler overhead |
| Read filter quality | tool-specific | Can prune input early |

## 3. Hardware homogeneity — much stricter than CPU

CPU vintage differences gave us a ~35 % outlier (isca071 in samtools sort).
**GPU vintage differences are 3-10x**, sometimes more if the older GPU lacks
tensor cores entirely. A V100 vs A100 result is fundamentally different data,
not noise.

### Always pin GPU type

```
#SBATCH --gres=gpu:a100:1     # NOT --gres=gpu:1
```

`--gres=gpu:1` lets SLURM hand you any GPU it has free, which is useless for
benchmarking. Available types on this cluster: `a100`, `l40s`, `h100`, `v100`
(check with `sinfo -O Gres,Partition`).

### Capture per-replicate GPU identity

In every replicate's CSV row, record:

- `gpu_model` (from `nvidia-smi --query-gpu=name --format=csv,noheader`)
- `gpu_driver_version` (from `nvidia-smi --query-gpu=driver_version`)
- `gpu_memory_total_mb` (from `--query-gpu=memory.total`)
- `cuda_runtime_version` (from inside the container, `nvcc --version`)

If two replicates of a "single condition" land on different GPU types, the
study has been silently confounded.

### Stratify analysis by GPU type

In `summarise_stage.R`, add `gpu_model` as a facet variable. Don't pool data
across GPU types — report per-GPU medians.

## 4. SLURM partitions

cpushort doesn't help for GPU jobs. On MSKCC HPC:

| Partition | Time limit | Use when |
|---|---|---|
| `componc_gpu_int` | 1 day | Interactive testing |
| `componc_gpu_batch` | 7 days | Long basecalling runs |
| `componc_gpu_preem` | 7 days | Cheap, but risk eviction (DON'T use for benchmarks) |
| `gpu` (default) | 7 days | Default; mixed GPU types |
| `gpushort` | 2 hours | Short basecalls only |

For benchmarking, `componc_gpu_int` (1-day, batch-friendly enough) or `gpu` are
the right pools. Avoid `componc_gpu_preem` — preemption mid-run wrecks
measurement.

Quick capacity check before submitting:

```bash
sinfo -p gpu,componc_gpu_int -O 'NodeList,Gres,GresUsed,State'
```

## 5. Container `--nv` is mandatory

The standard SIF wrapper from `apptainer_vs_conda.md` will **silently** miss
the GPU without `--nv`:

```bash
# WRONG — runs on CPU only, may hang or produce garbage
apptainer exec --bind /data1 dorado.sif dorado basecaller ...

# RIGHT — exposes /dev/nvidia* to the container
apptainer exec --nv --bind /data1 --bind /tmp dorado.sif dorado basecaller ...
```

`--nv` activates the nvidia-container-toolkit hook which mounts the host's CUDA
runtime + driver libs into the container. The container's CUDA toolkit version
must be **≤** the host driver's CUDA version. Verify before benchmarking:

```bash
# Host
nvidia-smi --query-gpu=driver_version,cuda_version --format=csv,noheader
# Container
apptainer exec --nv <sif> nvcc --version
```

If container's `nvcc` reports a newer CUDA than the host driver supports, the
job will fail at first kernel launch.

## 6. nvidia-smi sidecar — the new monitoring primitive

`/usr/bin/time -v` captures **CPU** RSS only. GPU memory and utilisation need
a sidecar process running during the job.

The pattern (already implemented in `03_run_one_gpu.sh.template`):

```bash
# Start sampling at 1 Hz before the timed command
GPU_LOG="$OUT_DIR/$RUN_ID.gpu.csv"
nvidia-smi --query-gpu=timestamp,index,memory.used,utilization.gpu,utilization.memory,power.draw,temperature.gpu \
           --format=csv,noheader,nounits -l 1 > "$GPU_LOG" &
GPU_MON_PID=$!
trap "kill $GPU_MON_PID 2>/dev/null" EXIT INT TERM

# ... timed command ...

kill $GPU_MON_PID 2>/dev/null
trap - EXIT INT TERM

# Parse GPU log for peak memory + mean util + mean power
PEAK_GPU_MEM_MB=$(awk -F',' 'NR>0 && $3+0 > max { max=$3+0 } END { print max+0 }' "$GPU_LOG")
MEAN_GPU_UTIL=$(awk -F',' '{ sum+=$4+0; n++ } END { if (n>0) printf "%.1f", sum/n; else print "0" }' "$GPU_LOG")
MEAN_GPU_POWER=$(awk -F',' '{ sum+=$6+0; n++ } END { if (n>0) printf "%.1f", sum/n; else print "0" }' "$GPU_LOG")
```

New CSV columns added to the runner output: `gpu_model`, `gpu_driver`,
`gpu_count`, `peak_gpu_mem_mb`, `mean_gpu_util_pct`, `mean_gpu_power_w`,
`mean_gpu_temp_c`.

### Sampling rate trade-off

- 1 Hz (`-l 1`) is fine for jobs >30 s. Captures the steady state but may miss
  brief startup spikes.
- 10 Hz (`-lms 100`) for short jobs (<30 s) where you want to see warm-up.
- Don't go faster than 10 Hz — nvidia-smi itself starts to consume measurable
  CPU.

## 7. Subsampling — different per input format

Stage 5 (input-size scan) needs reproducible subsamples. By format:

| Input | Reproducible subsample |
|---|---|
| pod5 (ONT raw) | `pod5 subset --threads 8 input.pod5 -o sub.pod5 --include-fraction <f>` (uses fixed hash, deterministic) |
| pod5 directory | randomly select `<f> × N` files from `pod5_pass/` (use `python -c "import random; random.seed(42); ..."`) |
| FAST5 (legacy ONT) | similar to pod5; older tooling, slower |
| FASTQ (already-basecalled) | `seqkit sample -p <f> -s 42 in.fq.gz -o out.fq.gz` |
| BAM (for fq2bam alignment) | `samtools fastq` then `seqkit sample` |

For dorado specifically, **subsample the pod5 directory by file count** — each
pod5 file holds ~4000 reads, so 10 % is approximately N_files / 10. This
preserves the per-channel batching dorado is optimised for.

## 8. Stage adaptations

### Stage 0 (setup) — additional fields
- GPU type (`a100`, `l40s`, `h100`)
- GPU count
- CUDA driver / toolkit version
- Container path with verified `--nv` compatibility

### Stage 1 (preflight) — additional probes
```bash
nvidia-smi -L                                      # GPU model + UUID list
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
nvcc --version                                     # CUDA toolkit (in container)
```

Add to `<input>.preflight.yaml`.

### Stage 2 (OFAT) — different factors
Use the dorado / aligner / variant-caller menu in §2 above. Skip `-m` and
compression — they're CPU-tool concepts.

### Stage 4 (build mode + alternatives) — adapt comparators
- Build modes: container (with `--nv`) vs native CUDA install. Skip "conda" —
  conda CUDA installs are a maintenance nightmare and rarely used in production.
- Alternatives: dorado vs guppy vs bonito (basecallers); fq2bam vs minimap2
  (aligners); DeepVariant vs Clair3 (variant callers).

### Stage 5 (input-size scan) — by sample count or signal duration
For basecallers: scan by total signal duration (sum of pod5 sample counts), not
by file count. Wall scales with signal volume, not with file fragmentation.

### Stage 7 (cost accounting) — energy term

GPU cost has two components:

```
cost_per_sample = wall_hours × (rate_per_gpu_hour
                              + watts / 1000 × rate_per_kWh)
```

Default rates if user doesn't supply local values:
- A100 rental: $1.50/hour (cloud-equivalent, varies)
- L40S rental: $0.80/hour
- H100 rental: $3.00/hour
- Power: $0.12/kWh
- A100 TDP: 400 W; L40S TDP: 350 W; H100 TDP: 700 W

For a 6-hour A100 basecall:
- GPU cost: 6 × $1.50 = $9.00
- Energy: 6 × 0.4 × $0.12 = $0.29

So GPU rental dominates; energy is ~3 % of total. Include both for honesty —
academic users may zero out the GPU-rental term but keep energy as a publishable
metric.

## 9. Tool-specific notes

### dorado

- Always confirm the model **and** the chemistry match. dorado will silently
  produce garbage if you basecall a 4 kHz pod5 with a 5 kHz model. Preflight
  must capture pod5 sample rate via `pod5 inspect summary`.
- `--reference <fasta>` makes dorado emit aligned BAM directly — much faster
  than `dorado basecaller | samtools sort` for whole-genome runs. Test both
  modes in Stage 4.
- `--mm2-opts "-Y"` for soft-clipping; common in our pipelines.
- Mod-base calls cost roughly 30-50 % per head. `5mCG_5hmCG,6mA` is roughly
  2× the wall of basecalling alone.
- See `rules/igv.md` for downstream visualisation gotchas with mod-base BAMs.

### Parabricks (fq2bam, haplotypecaller)

- License gate — many features need a license key. Confirm before benchmarking.
- Single-GPU vs multi-GPU scaling is in the docs; verify empirically.
- The `bam2fq` step is GPU-accelerated; benchmark separately if you're using
  it as part of a remap.

### DeepVariant

- Model selection (`--model_type`) matters more than thread count. Test
  WGS / WES / ONT / hybrid models.
- `--num_shards` is the parallelism knob; scale to GPU count.

## 10. Quick reference: GPU runner template

`scripts/03_run_one_gpu.sh.template` — copy this for any GPU tool. It's a
strict superset of the CPU runner: same flock CSV append, same GNU-time wrap,
plus the nvidia-smi sidecar, GPU identity capture, and apptainer `--nv` for
containerized invocations.

Edit only the `# === Build command ===` block and the CSV header / row to add
your tool-specific factors.
