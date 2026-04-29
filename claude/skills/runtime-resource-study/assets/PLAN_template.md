# {{TOOL_NAME}} {{COMMAND}} — benchmarking plan (v0.1)

- **Author**: {{USER}}
- **Date**: {{DATE}}
- **Tool**: {{TOOL_NAME}} {{COMMAND}}, v{{TOOL_VERSION}}
- **Status**: Draft

## 1. Aim

[Brief: what question is this study answering?]

## 2. Input data

Primary calibration input: `[FILL IN]`

Preflight metadata (filled in by `src/01_inspect_input.sh`):

| Field | Value |
|---|---|
| Format | [FILL IN] |
| File size | [FILL IN] |
| Total records | [FILL IN] |
| Primary records | [FILL IN] |
| Mean bytes per record | [FILL IN] |

Validation inputs (Stage 6):

[FILL IN: list of held-out inputs ~10× larger than calibration]

Subsamples (Stage 5, seed=42):

[FILL IN: list of fractions and resulting record counts]

## 3. Factors to vary (Stage 2 OFAT)

| Factor | Levels | Flag | Why it matters |
|---|---|---|---|
| Threads | 1, 2, 4, 8, 16, 32 | -@ / -t | Primary parallelism axis |
| [FILL IN] | | | |

## 4. Methodology controls

[Standard non-negotiables — copy from skill SKILL.md.]

## 5. Stage 3 (factorial) factor selection

After Stage 2, the 4 factors with biggest effect:

[FILL IN: results from Stage 2 to pick]

## 6. Stage 4 build modes / alternatives

| Mode | Path |
|---|---|
| Container | [FILL IN: SIF path] |
| Conda | [FILL IN: env path] |
| Native | [FILL IN: path or "not built"] |
| Alt-impl 1 | [FILL IN: alternative tool] |

## 7. Open questions

- [ ] [FILL IN]
- [ ] [FILL IN]

## 8. Stage progress

- [ ] Stage 0 — Setup
- [ ] Stage 1 — Preflight
- [ ] Stage 2 — OFAT scan
- [ ] Stage 3 — Confirmation factorial
- [ ] Stage 4 — Build mode + alt-impl
- [ ] Stage 5 — Input-size scan
- [ ] Stage 6 — Out-of-sample validation
- [ ] Stage 7 — Variance + cost + report

## 9. Findings log

(Append to this section as the study proceeds — what was surprising,
what was non-obvious, what corrections were needed.)

[FILL IN as you go]
