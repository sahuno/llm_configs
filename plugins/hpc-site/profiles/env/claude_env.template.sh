#!/usr/bin/env bash
# Claude Code environment variable template
# Author: Samuel Ahuno
# Purpose: Portable reference of Claude Code env vars for setting up new machines.
#
# Usage on a new machine:
#   1. cp claude_env.template.sh claude_env.local.sh
#   2. Fill in real values in claude_env.local.sh (never commit it; it is gitignored)
#   3. Add to ~/.zshrc or ~/.bashrc:
#        [ -f /path/to/claude_env.local.sh ] && source /path/to/claude_env.local.sh
#
# Reference: https://docs.anthropic.com/en/docs/claude-code/settings
# Only uncomment and set variables you actually need.

# ---------------------------------------------------------------------------
# Authentication (choose ONE of the following)
# ---------------------------------------------------------------------------
# Direct Anthropic API key (most common for personal use):
# export ANTHROPIC_API_KEY=""

# Alternative bearer token (for custom auth proxies):
# export ANTHROPIC_AUTH_TOKEN=""

# Custom API gateway / proxy base URL (e.g. LiteLLM, internal gateway):
# export ANTHROPIC_BASE_URL=""

# Extra headers sent on every API call (e.g. org routing). Format: "Key: value\nKey2: value2"
# export ANTHROPIC_CUSTOM_HEADERS=""

# ---------------------------------------------------------------------------
# Cloud provider routing (mutually exclusive with direct API key)
# ---------------------------------------------------------------------------
# Route through AWS Bedrock:
# export CLAUDE_CODE_USE_BEDROCK=1
# export AWS_REGION="us-east-1"

# Route through Google Vertex AI:
# export CLAUDE_CODE_USE_VERTEX=1
# export CLOUD_ML_REGION="us-east5"
# export ANTHROPIC_VERTEX_PROJECT_ID=""

# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------
# Override default model (e.g. "claude-opus-4-6", "claude-sonnet-4-6"):
# export ANTHROPIC_MODEL=""

# Override small/fast model used for background tasks (e.g. "claude-haiku-4-5-20251001"):
# export ANTHROPIC_SMALL_FAST_MODEL=""

# ---------------------------------------------------------------------------
# Output and thinking limits
# ---------------------------------------------------------------------------
# Cap extended thinking tokens (integer):
# export MAX_THINKING_TOKENS=""

# Cap final output tokens per response (integer):
# export CLAUDE_CODE_MAX_OUTPUT_TOKENS=""

# Cap MCP tool response size (integer, bytes):
# export MAX_MCP_OUTPUT_TOKENS=""

# ---------------------------------------------------------------------------
# Tool timeouts
# ---------------------------------------------------------------------------
# MCP server startup timeout (ms):
# export MCP_TIMEOUT="30000"

# Individual MCP tool call timeout (ms):
# export MCP_TOOL_TIMEOUT="60000"

# Bash tool default timeout (ms):
# export BASH_DEFAULT_TIMEOUT_MS="120000"

# Bash tool maximum timeout (ms):
# export BASH_MAX_TIMEOUT_MS="600000"

# Bash tool max captured output bytes:
# export BASH_MAX_OUTPUT_LENGTH=""

# Keep Bash working directory within the project root:
# export CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR="1"

# API key helper script TTL (ms):
# export CLAUDE_CODE_API_KEY_HELPER_TTL_MS=""

# ---------------------------------------------------------------------------
# Privacy / telemetry / updates
# ---------------------------------------------------------------------------
# Disable the built-in auto-updater:
# export DISABLE_AUTOUPDATER="1"

# Disable anonymized telemetry:
# export DISABLE_TELEMETRY="1"

# Disable crash / error reporting:
# export DISABLE_ERROR_REPORTING="1"

# Disable non-essential model calls (e.g. background summarization):
# export DISABLE_NON_ESSENTIAL_MODEL_CALLS="1"

# Disable bug-reporting slash command:
# export DISABLE_BUG_COMMAND="1"

# Suppress cost warnings:
# export DISABLE_COST_WARNINGS="1"

# Cut all non-essential outbound traffic (strictest):
# export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"

# ---------------------------------------------------------------------------
# Network / proxy
# ---------------------------------------------------------------------------
# Forward Claude Code traffic through an HTTP proxy:
# export HTTP_PROXY=""
# export HTTPS_PROXY=""

# ---------------------------------------------------------------------------
# Notes on variables set automatically by Claude Code (do NOT export these)
# ---------------------------------------------------------------------------
# CLAUDECODE, CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_EXECPATH are injected by the
# Claude Code runtime at startup. Setting them manually has no effect.
