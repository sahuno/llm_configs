---
tool: rsync (via irismount/bulk-pull.sh) writing into a OneDrive CloudStorage destination
version_observed: "rsync 3.5.0 (homebrew, protocol 32); OneDrive 26.150.0804; macOS 26.6.2 build 25G83"
date: 2026-09-07
status: active   # active | fixed-upstream | superseded
detect_cmd: |
  # 1. Is the destination inside a cloud-sync tree? (`mount` will NOT tell you — File Provider, not a mount)
  case "${DEST:?set DEST first}" in *"/Library/CloudStorage/"*) echo "RISK: cloud-sync destination";; *) echo "ok: plain local destination";; esac
  # 2. Did any past attempt die on a LOCAL write timeout rather than a network drop?
  for f in ~/.iris-transfers/*.log; do printf '%s io11=%s ssh255=%s stall30=%s\n' "$(basename "$f")" \
    "$(grep -ac 'code 11' "$f")" "$(grep -ac 'code 255' "$f")" "$(grep -ac 'code 30' "$f")"; done
---
- **A long rsync into `~/Library/CloudStorage/OneDrive-*` dies mid-file with a *local* write error, not a network one.** Confirmed 2026-09-06 pulling `iris:/data1/greenbab/users/ahunos/apps/openSource/DSS/results` (95 G, 1197 files) into a OneDrive folder. The exact failure, after 3 h 52 m and 62.7 G transferred:
  ```
  rsync: [receiver] write failed on ".../dss_output/dml_test_QSTAT_vs_SETDB1i.tsv": Operation timed out (60)
  rsync error: error in file IO (code 11) at receiver.c(644) [receiver=3.5.0]
  ```
  `Operation timed out (60)` is `ETIMEDOUT` returned by `write()` on the destination. The remote side was healthy; the OneDrive file provider stopped accepting writes on a multi-GB file for long enough that the kernel gave up on the write. It is reproducible-in-kind on any large file, and hits later in the transfer as file sizes grow.
- **Read the exit code before blaming the VPN — one log had three distinct causes.** In `~/.iris-transfers/apps_openSource_DSS_results_20260906_192120.log`, seven attempts over seven hours:

  | exit | rsync meaning | actual cause here | log signature |
  |---|---|---|---|
  | 30 | timeout in data send/receive | connection went half-dead, `--timeout=300` fired | no error text, just stops |
  | 255 | ssh transport error | **VPN down** — ssh could not resolve the host at all | `ssh: Could not resolve hostname islogin01.mskcc.org` |
  | 11 | error in file IO | **OneDrive** stalled accepting writes locally | `write failed on "<dest path>": Operation timed out (60)` |

  Code 255 with a DNS failure means the tunnel is gone. Code 11 means the tunnel was fine and your *laptop* was the problem. Fixing the VPN does nothing for a code 11.
- **`mount` cannot detect a cloud-sync destination.** `mount | grep -i cloudstorage` returns nothing on macOS 26 — OneDrive is a File Provider extension, not a mounted filesystem. Detect it by path prefix (`*/Library/CloudStorage/*`), as in `detect_cmd`.
- **The fix that is actually measured: let `bulk-pull.sh` retry.** Its loop restarts rsync after `RETRY_WAIT` (60 s) and `--partial-dir` resumes the interrupted file rather than restarting it. The transfer above completed on attempt 7 with `rc=0`, and the destination then matched the source exactly (1197 files, 101 740 273 985 bytes both sides). No manual intervention was required or helpful.
- **Do NOT "fix" this by staging to local disk first.** It is the obvious suggestion and it does not generalize: pull sizes are not bounded by local free space, so a workflow that assumes a full local staging copy will fail on the first pull bigger than the disk. `--partial-dir` (which stages only the *one* in-flight file outside the destination) is the version of that idea that is safe, and `bulk-pull.sh:41` already does it. Untested alternatives, if the retry loop ever proves insufficient: pausing OneDrive sync for the duration, or `--bwlimit` to slow the writer. Neither has been measured — do not present them as known fixes.
- **Never conclude "the transfer died" from `ps` alone.** During the 60 s `RETRY_WAIT` sleep there is no rsync process, and the wrapper is still very much alive. On 2026-09-06 a `ps` check landed in exactly that gap, and a manual rsync was launched 34 s after the wrapper had already begun attempt 7 — two rsyncs then ran into the same destination sharing one `--partial-dir` for 2 h 17 m. It happened to end clean, but concurrent writers on the same partial file can corrupt it. **Check `~/.iris-transfers/*.log` for a recent `--- attempt N ---` line before touching anything.**
- **Verification after any pull into a cloud-sync folder** — compare both sides explicitly, since a masked code 11 leaves a plausible-looking partial tree:
  ```bash
  # remote side
  ssh iris "cd <remote> && find . -type f | wc -l && du -sb . | cut -f1"
  # local side
  find <dest> -type f | wc -l; find <dest> -type f -exec stat -f %z {} + | awk '{s+=$1} END {print s}'
  ```
  Byte totals must match exactly. Note this checks size, not content; a true content check is `rsync -n --checksum`, but against a OneDrive destination that forces rehydration of every offloaded file and is slow enough to avoid unless a mismatch is suspected.
