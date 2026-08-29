- **Host SSL/CA env vars leak into apptainer SIFs and break httpx-based clients (huggingface_hub, requests).** On MSKCC HPC (RHEL 8) the host shell exports `SSL_CERT_FILE=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem` and `SSL_CERT_DIR=/etc/pki/...`. Apptainer inherits these into the container by default. Inside the SIF those paths don't exist, so any code that calls `ssl.create_default_context()` (which httpx does on init) crashes with `FileNotFoundError: [Errno 2] No such file or directory` for the missing bundle. **The crash is delayed**: `<tool> --help` and pure-Python imports work fine; the failure surfaces only when the first HTTP client is constructed (e.g. when sentence-transformers loads a model and calls into `huggingface_hub`, even with `HF_HUB_OFFLINE=1` — the client is still instantiated, just not used). Confirmed 2026-04-28 building `lab-rag-service/containers/lab-rag.def`: `lab-rag stats` worked, `lab-rag query` died on model load.
- **Diagnostic shortcut**: if `apptainer exec --cleanenv <sif> <cmd>` succeeds where `apptainer exec <sif> <cmd>` fails on the same host, you have an env-leak bug, not a build defect. `--cleanenv` is fine for one-off tests but is not a UX fix — users will paste the documented invocation, not yours.
- **Permanent fix in `%environment`**: unset every host env var that names a path the container doesn't have. Minimum set for SSL + Python:
  ```
  unset SSL_CERT_FILE
  unset SSL_CERT_DIR
  unset REQUESTS_CA_BUNDLE
  unset PYTHONPATH
  ```
  `PYTHONPATH` belongs on this list because host-level entries (user-site, conda envs, project src dirs) shadow container-bundled packages and surface as confusing `ImportError` / wrong-version bugs on otherwise-installed modules.
- **`%test` must exercise the network/HTTP path, not just `--help`.** A SIF that imports cleanly and prints help can still die the moment an HTTP client opens. The model-load smoke test catches this — e.g. for an embedding-model SIF:
  ```
  HF_HUB_OFFLINE=1 python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
  ```
  Add this to `%test` alongside the trivial `<tool> --help` check. Reference: `lab-rag-service/containers/lab-rag.def`.
- **This is independent of the `--fakeroot` / conda / apt-get rules in CLAUDE.md §6.** It's a runtime env-inheritance bug, not a build-time one — a clean `apptainer build` can produce a SIF that nonetheless fails at first run on the same host whose env shipped through. Build success is necessary but not sufficient; verify by running the published invocation in a fresh shell with no `--cleanenv`.
