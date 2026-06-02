# CLAUDE.md

Primary project memory for Claude Code. Keep this file compact; load referenced docs only when the task needs them.

## Project

AdaptCI is an ML-based test prioritization system for Java/Maven CI pipelines.

- Goal: rank tests so likely failures run earlier and CI feedback is faster.
- Primary metric: APFD (Average Percentage of Faults Detected).
- Ground truth: RTPTorrent CSVs in `data/repos/rtp-torrent/`.
- Models planned: XGBoost and LightGBM, trained offline, served through FastAPI, integrated later with GitHub Actions.
- Not a Maven replay tool: do not rerun `mvn test` to collect the historical dataset.

## Current State

Sprint 1 foundation is in progress.

- Existing: `requirements.txt`, `docker-compose.yml`, `src/`, `tests/`, `scripts/`, `notebooks/`, `data/features/`.
- RTPTorrent CSV data exists under `data/repos/rtp-torrent/`.
- Data helper scripts exist in `data/scripts/`.
- `README.md` is the command reference for setup, MLflow, project selection, and SQLite loading.
- Sprint tasks live in `docs/backlog/`; sprint planning lives in `docs/plan/`.

## Entry Points

- Select usable RTPTorrent projects: `data/scripts/select_rtp_projects.py`
- Load selected projects to SQLite: `data/scripts/load_rtp_dataset.py`
- Build feature artifacts: `scripts/data_pipeline.py`
- Package skeletons: `src/features/`, `src/models/`, `src/evaluation/`, `src/serving/`
- Experiment notebook: `notebooks/01_ground_truth_validation.ipynb`

## Must-Follow Rules

- Preserve `data/repos/rtp-torrent/`; it is source data.
- Generated feature artifacts belong under `data/features/`.
- Use `TimeSeriesSplit` for validation; never use `KFold` or random split for temporal history.
- Report ML results against baselines: Random, Alphabetical, and Most Recently Failed.
- APFD formula: `1 - (sum(rank_i) / (n_tests * n_faults)) + (1 / (2 * n_tests))`.
- Treat `javalang` as optional/fallible; wrap AST parsing so parse failures do not break pipelines.
- Python code should use type hints and no `import *`.
- Before proposing architecture changes, read `.claude/context/decisions-log.md`.

## Context Loading

- Use `README.md` for commands and generated artifact notes.
- Use `requirements.txt` for dependency versions instead of duplicating them here.
- Use `.claude/context/architecture-snapshot.md` only for architecture work.
- Use `.claude/context/results-snapshot.md` only for result interpretation.
- Use `.claude/commands/` only when authoring or debugging slash commands.
