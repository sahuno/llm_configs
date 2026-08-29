# Serving local LLMs on iris (vLLM in apptainer on componc_gpu_batch)

Lessons from the 2026-05-11 antVacDBCancer pubmed-vaccine-agent session, where 5 sbatch retries (~25 min wasted) chased problems that show up in a predictable order. Captured so the same checklist runs first next time.

## Partition + GPU selection (greenbab)

- **`componc_gpu` (no suffix) is NOT a valid partition.** Greenbab's allowed GPU partitions are `componc_gpu_int` (interactive), `componc_gpu_batch` (batch, 7-day), and `componc_gpu_preem` (preemptable). Plus `gpushort` for short jobs and `interactive`. See `references/mskcc_partitions.md` for the full list.
- **componc_gpu_batch layout** (confirmed 2026-05-11 via `scontrol show partition`):
    - 10 nodes / 640 cpu / 40 GPUs / ~1 TB RAM per node, 7-day time limit
    - GPU mix: **24 × A100 (iscb001-006) + 16 × L40S (iscf029-031, iscxf001)** — heterogeneous, scheduler may land you on either
    - All A100 nodes inspected so far are **A100 80GB PCIe**, not 40GB. SLURM doesn't expose the memory variant as a feature, so request `--gres=gpu:a100:1` and pray. So far on iscb00X it's always been 80GB.
- **`--gres=gpu:1` will land you on whatever GPU is free first.** For 30B-class BF16 models (~60 GB on disk), L40S 48GB cannot hold the weights — vLLM will OOM at load time. **Always force the GPU type with `--gres=gpu:a100:1`** unless you've explicitly quantized the model to fit smaller cards. Fits-or-OOMs at load time is loud, but it wastes ~3 min of the cold-start budget.
- **WekaFS is the underlying filesystem for `/data1`.** vLLM's safetensors auto-prefetch is disabled because Weka isn't a recognized network FS (NFS/Lustre). Throughput is still fine (~700 MB/s read sustained on a 13-shard load), but if you want explicit prefetching: `--safetensors-load-strategy=prefetch`.

## `huggingface_hub` 1.0 CLI rename (bites the model-download step)

- **`huggingface-cli` is deprecated and no longer works in huggingface_hub 1.0.** The binary exists, prints "deprecated, use `hf` instead", and exits without downloading. Any script written before late-2025 referencing `huggingface-cli download …` will silently no-op.
- **Replacement**: `hf download <repo_id> --local-dir <dir> [--token $HF_TOKEN]`.
- **Flag removed**: `--local-dir-use-symlinks False` no longer exists. The new default behavior is what we always wanted (real files in `--local-dir`, no symlink farm to the HF cache).
- **`[hf_transfer]` extra is gone too.** Used to be `pip install 'huggingface_hub[hf_transfer]'` for the Rust parallel downloader. Now `huggingface_hub` 1.0 bundles **hf-xet** (the Xet protocol) as a regular dep, on by default. The env var `HF_HUB_ENABLE_HF_TRANSFER=1` is now a no-op.
- **Installing the CLI**: `pip install --user 'huggingface_hub'` (single name, no extras). `hf-xet` comes with.

## vLLM Docker/SIF image quirks (`vllm/vllm-openai:latest`)

The image is convenient (`apptainer pull docker://vllm/vllm-openai:latest`, ~7 GB) but its CLI surface changes between minor versions and the runtime makes assumptions that bite in apptainer:

- **`python` is not on `$PATH`, only `python3`.** `apptainer exec ... <sif> python -m vllm.entrypoints.openai.api_server` errors with `FATAL: "python": executable file not found in $PATH`. Use `python3`. The vLLM Docker `ENTRYPOINT` uses `python3` internally so you'd think `singularity run` works too — but with `exec` you must spell it out.
- **`--disable-log-requests` was renamed.** Newer vLLM uses `[--enable-log-requests | --no-enable-log-requests]`. To suppress per-request logging: `--no-enable-log-requests`. Old flag errors with `api_server.py: error: unrecognized arguments: --disable-log-requests` and vLLM exits before serving anything; the sbatch polling loop then sits for 10 min waiting for a server that already died.
- **Multimodal models need `--max-num-batched-tokens` ≥ `max_tokens_per_mm_item`.** Gemma 4 is multimodal (vision + text). Its image encoder emits up to **2496 tokens** per item, which exceeds vLLM's default `max_num_batched_tokens=2048`. Startup aborts with `ValueError: Chunked MM input disabled but max_tokens_per_mm_item (2496) is larger than max_num_batched_tokens (2048).` Fix: pass `--max-num-batched-tokens "$MAX_MODEL_LEN"` (we use 8192).
- **NemotronH is natively supported in vLLM ≥ 0.6.x — no `--trust-remote-code` needed.** The model card lists `custom_code`, but vLLM ships the architecture. The config dump literally prints `trust_remote_code=False` to stderr, which can confuse log-pattern monitors (see below).
- **The real "server is ready" log marker is `Application startup complete`**, not `Uvicorn running on`. The latter may or may not appear depending on the vLLM version's log config — monitors that key on `Uvicorn` miss readiness on newer images.
- **API-key behavior**: when vLLM is launched with `--api-key <token>`, the OpenAI-compat endpoints require that bearer token. When `--api-key` is OMITTED, vLLM accepts any non-empty bearer. The classifier needs to pass the same token via the `LOCAL_VLLM_API_KEY` env var.
- **`served-model-name` is just a client-side identifier**, decoupled from the actual model path. Set it to whatever you want clients to send as `model: <id>`.

## NVIDIA model IDs differ between HuggingFace and NIM

Same checkpoint, two namespaces, opposite capitalization conventions:

- **HuggingFace**: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` (capitalized, includes precision suffix: `-BF16` / `-FP8` / `-NVFP4`)
- **NIM API** (`https://integrate.api.nvidia.com/v1`): `nvidia/nemotron-3-nano-30b-a3b` (lowercase, no precision suffix)

If you script the HF id where the NIM id is wanted (or vice versa), you get a 404 with no hint that there's a casing/namespace issue. Verify both independently when wiring up a new NVIDIA model in both the `nvidia` provider (NIM) and the `local_vllm` provider (HF download).

## Performance reference points (componc_gpu_batch, A100 80GB PCIe)

For sizing-budget conversations and "is this slow?" sanity checks:

| Workload                         | Wall   | Per-paper | Notes |
|----------------------------------|--------|-----------|-------|
| vLLM cold load (60 GB BF16, cold WekaFS) | ~130 s | —       | First-time read |
| vLLM warm load (same model, warm cache)  | ~75 s  | —       | Subsequent runs |
| Gemma 4 31B BF16 (dense), 38 papers      | 143 s  | 3.8 s     | Memory-BW bound, ~30 tok/s/req |
| Nemotron-3 30B-A3B BF16 (MoE, 3B active), 38 papers | 29 s   | 0.77 s    | ~5× speedup tracks active-param ratio |

The MoE speedup is the headline: same on-disk size, ~10× less weight-read per decoded token, ~5× realized wall on serial requests. If you push to concurrent requests (asyncio HTTP client), continuous batching amortizes weight-read across the batch and you'd see another 5-10× throughput on either model.

## Filename convention when one provider serves many models

The `local_vllm` provider can host any HF checkpoint, so the old convention `relevance_classification.<provider>.json` collapses every served model to one file. The classifier's resume mode then sees "already done" and silently no-ops on the second model — confirmed 2026-05-11 on Gemma-then-Nemotron back-to-back.

Convention adopted on the antVacDBCancer pubmed-vaccine-agent branch:

- `relevance_classification.<provider>.json` — when served model == provider default (preserves committed legacy files)
- `relevance_classification.<provider>__<model-slug>.json` — when served model differs from default

Where `<model-slug>` is the HF basename, lowercased, non-alphanum→`-`. E.g. `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` → `nvidia-nemotron-3-nano-30b-a3b-bf16`.

Comparison/aggregation scripts should **discover files by glob** instead of iterating a hard-coded provider tuple — otherwise they miss per-model files.

## Monitor-filter discipline (incidental but bit us twice)

When polling SLURM jobs with grep-based log filters:

- **Use anchored regex for error detection**: `^[A-Z]+Error:`, `raise [A-Z]+Error`, `^FATAL:`. Bare keyword matches (`trust_remote_code`, `Error`, `ValueError`) match config dumps and benign warnings.
- **The vLLM startup config dump prints every config knob's value**, including `trust_remote_code=False`. Pattern matchers keying on the literal substring `trust_remote_code` will false-positive on every successful startup.
- **Don't pair `tail -f log | grep -m 1 PATTERN` with single-notification expectations** — if the log goes quiet after the match, `tail` doesn't get SIGPIPE and the pipeline hangs. For "wait until ready" use `until grep -q PATTERN log; do sleep 0.5; done` in a `run_in_background` bash.
- **Coverage matters**: filters must match every terminal state, not just the happy path. A monitor that only watches for `Application startup complete` is silent through OOM crashes and unknown-arg exits — silence ≠ success.

## Process lesson — patch carefully, grep after

When changing a function signature in a long file (like adding a `model` argument to `_out_paths(provider)`), **always `grep -n <function_name>` after the edit** to enumerate all callers. We patched the `main()` call site, missed the `write_outputs()` call site, the job ran for 5 papers then died on the every-5-papers checkpoint write with `TypeError: missing 1 required positional argument`. The grep would've taken 2 seconds and saved a full sbatch retry.

## Cross-references

- `references/mskcc_partitions.md` — partition selection and the slow-cpu `--exclude=isca071` for benchmarks
- `references/slurm_mcp.md` — slurm-mcp quirks (mem/mem-per-cpu conflict, log path redirection)
- `singularity-build` skill → `references/env_leak.md` — host env vars leaking into apptainer SIFs (relevant for any apptainer-served thing, not just vLLM)
- `references/apptainer_vs_conda.md` — when to prefer SIF over a conda env (cold-start tax)
