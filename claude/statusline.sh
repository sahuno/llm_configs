#!/bin/sh
# Claude Code statusLine command
# Derived from PS1='\s:\h:\W \! \$ ' in ~/.bashrc
# \s -> bash  \h -> hostname -s  \W -> basename of cwd  \! -> omitted  \$ -> removed (trailing prompt char)

input=$(cat)

host=$(hostname -s)
full_cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
cwd="${full_cwd:-$(pwd)}"
case "$cwd" in
    "$HOME"/*) cwd="~${cwd#"$HOME"}" ;;
    "$HOME") cwd="~" ;;
esac
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
transcript=$(echo "$input" | jq -r '.transcript_path // empty')

# Prefix: bash:host:full_cwd
prefix="bash:${host}:${cwd}"

# Context window usage
ctx_info=""
if [ -n "$used" ]; then
    ctx_info=" | ctx:$(printf '%.0f' "$used")%"
fi

# Model name
model_info=""
if [ -n "$model" ]; then
    model_info=" | ${model}"
fi

# Last message time (from transcript), e.g. "1m ago"
last_info=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
    last_line=$(jq -rc 'select(.type=="user" or .type=="assistant") | "\(.timestamp)|\(.type)"' "$transcript" 2>/dev/null | tail -1)
    if [ -n "$last_line" ]; then
        last_ts="${last_line%%|*}"
        last_role="${last_line##*|}"
        if date -j -u -f "%Y-%m-%dT%H:%M:%S" "${last_ts%%.*}" "+%s" >/dev/null 2>&1; then
            # BSD date (macOS)
            last_epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%S" "${last_ts%%.*}" "+%s" 2>/dev/null)
        else
            # GNU date (Linux)
            last_epoch=$(date -u -d "${last_ts}" "+%s" 2>/dev/null)
        fi
        now_epoch=$(date "+%s")
        if [ -n "$last_epoch" ]; then
            diff=$((now_epoch - last_epoch))
            if [ "$diff" -lt 60 ]; then
                ago="${diff}s"
            elif [ "$diff" -lt 3600 ]; then
                ago="$((diff / 60))m"
            else
                ago="$((diff / 3600))h"
            fi
            last_info=" | ${last_role}:${ago} ago"
        fi
    fi
fi

printf '%s%s%s%s' "$prefix" "$model_info" "$ctx_info" "$last_info"
