---
name: scatter-gather-fires
tags: [skill-trigger]
runs: 1
max_turns: 4
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob, Grep]
---
Calling DMRs on whole-genome bedMethyl files takes forever. Can I just split it by chromosome and merge the results afterwards?
