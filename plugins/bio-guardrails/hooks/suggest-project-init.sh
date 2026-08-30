#!/bin/bash
# SessionStart: point out when a directory is an analysis project that cannot
# identify itself, and stay quiet otherwise.
# Author: Samuel Ahuno
#
# The original proposal (inDevelopment/hooks_suggestions.md #1) fired on every
# UserPromptSubmit and warned whenever config.yaml and data/ were both absent.
# That nags in every directory that is not an analysis project — including this
# repo — and a warning shown every prompt stops being read by the third one.
#
# This fires once per session and only when there is positive evidence the
# directory IS an analysis project (config.yaml, sample_sheet.tsv or data/)
# while lacking the project CLAUDE.md that would let a session self-identify.
# Silence everywhere else is the correct behaviour, not a gap.

# No project markers -> not an analysis project -> nothing to say.
if [ ! -f config.yaml ] && [ ! -f sample_sheet.tsv ] && [ ! -d data ]; then
  exit 0
fi

# Already self-identifying: Claude Code loads this automatically.
[ -f CLAUDE.md ] && exit 0

cat <<'MSG'
This looks like an analysis project (config.yaml / sample_sheet.tsv / data/) but
has no project-level CLAUDE.md, so each session has to ask what it is working on.

`/init-bio-project` writes one — domain, genome build, aims, status, and a
pointer to the progress log — after which sessions self-identify. If the project
is already scaffolded, adding CLAUDE.md alone is enough.
MSG
exit 0
