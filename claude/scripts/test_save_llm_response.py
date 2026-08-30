#!/usr/bin/env python3
"""Run the harness-agnostic tests."""

from __future__ import annotations

import runpy
from pathlib import Path

target = (
    Path(__file__).resolve().parents[2]
    / "cli_coding_agents_setups"
    / "save-llm-response"
    / "test_save_llm_response.py"
)
runpy.run_path(str(target), run_name="__main__")
