---
name: singularity-build-fires
tags: [skill-trigger]
runs: 1
max_turns: 4
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob, Grep]
---
My apptainer build for modkit keeps dying with exit status 255 on the cluster, I don't have sudo. Can you help me write a working .def file?
