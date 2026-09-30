# AI engineering: LLM applications and ML on genomic data

Moved from CLAUDE.md §5 on 2026-09-30. Small-n cross-validation traps are in the `analysis-gotchas` skill (`references/cv_at_small_n.md`).

### LLM Applications
- **Frameworks**: Claude API, OpenAI API, LangChain, LlamaIndex — ask user which unless context is clear.
- **Prompt versioning**: Store prompts as separate text/yaml files, never inline long prompts as string literals.
- **Evaluation**: Define at least one quantitative metric before building. Log all LLM calls with input/output/latency/cost.
- **Experiment tracking**: Use MLflow, Weights & Biases, or a structured JSON log. Never rely on terminal output alone.

### ML for Genomics / Classical ML
- **Train/val/test split**: Always hold out a test set that is never touched until final evaluation. For genomic data, split by chromosome or patient to avoid data leakage.
- **Hyperparameter search**: Use Optuna or sklearn GridSearchCV. Log all trials.
- **Deployment**: Containerize models. Provide a predict script with clear input/output schema.
- **Reproducibility**: Pin all library versions. Export conda environment or requirements.txt at experiment completion.
