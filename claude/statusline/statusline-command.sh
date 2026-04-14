#!/bin/sh
# Claude Code statusLine command
# Derived from PS1='\s:\h:\w \! \$ ' in ~/.zshrc

input=$(cat)

host=$(hostname -s)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Build PS1-style prefix: shell:host:cwd
prefix="zsh:${host}:${cwd}"

# Build context info
ctx_info=""
if [ -n "$used" ]; then
    ctx_info=" | ctx:$(printf '%.0f' "$used")%"
fi

model_info=""
if [ -n "$model" ]; then
    model_info=" | ${model}"
fi

printf '%s%s%s' "$prefix" "$model_info" "$ctx_info"
