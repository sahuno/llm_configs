#!/usr/bin/env python3
"""Flatten a slurm-mcp PostToolUse payload into shell-readable lines.

Author: Samuel Ahuno

The payload is double-encoded: .tool_response is a JSON string whose .result is
another JSON string. Doing that in jq needs three chained invocations, which was
the last thing in the guardrails still requiring jq. This is a file rather than
an inline block because the job-list formatting needs nested quotes, and inline
quoting inside a bash heredoc is how the previous attempt broke.

Emits, one per line:
    1 job_id | 2 job_name | 3 command | 4 dry_run | 5 error | 6 submitted | 7 total
    8+ formatted job lines
Prints nothing and exits 0 if the payload is not parseable — this is a logger.
"""
import json
import sys


def _inner(value):
    """Decode a value that may be a JSON string wrapping a dict."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value if isinstance(value, dict) else None


def main() -> int:
    try:
        outer = json.load(sys.stdin)
    except (ValueError, TypeError):
        return 0
    resp = _inner(outer.get("tool_response"))
    data = _inner(resp.get("result")) if isinstance(resp, dict) else None
    if not isinstance(data, dict):
        return 0

    def get(key, default=""):
        value = data.get(key, default)
        return "" if value is None else str(value)

    for key, default in (("job_id", ""), ("job_name", ""), ("command", ""),
                         ("dry_run", "false"), ("error", ""), ("submitted", ""),
                         ("total", "0")):
        print(get(key, default))

    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        print("  - Job {} — {} (step {})".format(
            job.get("job_id", "?"), job.get("script", "unknown"), job.get("step", "?")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
