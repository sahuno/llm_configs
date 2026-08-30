#!/usr/bin/env python3
"""Shim — canonical saver is cli_coding_agents_setups/save-llm-response/save_llm_response.py."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_CANDIDATES = [
    Path.home() / ".llm_configs" / "save_llm_response.py",
    Path(__file__).resolve().parents[2] / "cli_coding_agents_setups" / "save-llm-response" / "save_llm_response.py",
]
for _path in _CANDIDATES:
    if _path.is_file() and _path.resolve() != Path(__file__).resolve():
        sys.argv[0] = str(_path)
        runpy.run_path(str(_path), run_name="__main__")
        raise SystemExit(0)
sys.stderr.write("save_llm_response.py not found. Run cli_coding_agents_setups/save-llm-response/install.sh\n")
raise SystemExit(1)
