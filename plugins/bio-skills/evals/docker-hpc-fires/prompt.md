---
name: docker-hpc-fires
tags: [skill-trigger]
runs: 1
max_turns: 4
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob, Grep]
---
Can you dockerize bcftools 1.21 for me so I can pull it with apptainer on the cluster, built by GitHub Actions since I have no docker on my laptop?
