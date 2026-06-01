# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FSB-Capstone is an academic thesis project building an **ML-based test prioritization system for Java/Maven CI pipelines**. The goal is to rank test execution order so that the most likely failing tests run first (fail-fast), reducing CI feedback latency. The primary evaluation metric is **APFD** (Average Percentage of Faults Detected).

The repository is currently in the **planning phase** — sprint backlogs exist in `docs/`, but source code has not yet been implemented. Implementation follows an 8-sprint roadmap.

## Commands

### Python Environment Setup (Sprint 1)
```bash
pyenv local 3.11
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### MLflow Tracking Server
```bash
docker compose up -d        # Starts MLflow UI at http://localhost:5000
docker compose down
```

### Data Pipeline
```bash
python scripts/extract_ci_history.py --repo-path data/repos/commons-lang --limit 200
python scripts/data_pipeline.py --repo-path <path>   # Produces data/features/full_features.parquet
```

### Model Training
```bash
python scripts/tune_xgboost.py     # 50 Optuna trials logged to MLflow
python scripts/tune_lgbm.py
python scripts/cross_validate.py   # 5-fold TimeSeriesSplit stability analysis
```

### Prediction Service
```bash
uvicorn src.serving.app:app --host 0.0.0.0 --port 8000
# Or via Docker:
docker compose up              # FastAPI at http://localhost:8000, Swagger at /docs
```

### Dashboard
```bash
cd dashboard
npm install
npm run dev    # Vite dev server at http://localhost:3000
npm run build
```

### Tests
```bash
pytest tests/                              # Full suite
pytest -v tests/test_commit_extractor.py  # Single file
pytest -v tests/test_apfd.py::test_name   # Single test
```

## Architecture

### Three-Phase Pipeline

**1. Offline Training** (`scripts/`, `src/features/`, `src/models/`, `src/evaluation/`)
- Clone target Java repos under `data/repos/` (Apache Commons Lang/Collections, Spring Framework)
- `scripts/extract_ci_history.py` replays commits: checkout → `mvn test` → parse Surefire XML → store in `data/test_history.db` (SQLite)
- `src/features/` extractors produce `data/features/full_features.parquet` with ~25 features per (commit, test) pair
- XGBoost and LightGBM models trained with Optuna hyperparameter search, all experiments logged to MLflow
- Best model promoted to MLflow Model Registry as `test-predictor/Production`

**2. Online Prediction** (`src/serving/`)
- FastAPI loads model from MLflow Registry on startup via `mlflow.sklearn.load_model("models:/test-predictor/Production")`
- `POST /predict` accepts a `CommitPayload` (repo path, commit SHA, test IDs, threshold) and returns a `PredictionResponse` (ranked tests, failure probabilities, early-exit index)
- Early exit: stop running tests once cumulative failure probability exceeds `threshold` (default 0.85), targeting ≥25% CI time reduction at ≤5% false-negative rate

**3. CI Integration + Feedback Loop** (`github-action/`, `src/serving/`)
- Custom GitHub Actions action calls the FastAPI endpoint on each push
- Maven Surefire runs tests in predicted order via reordered test list
- Actual outcomes fed back to trigger drift detection (Population Stability Index, PSI > 0.2 = retrain)
- ReactJS dashboard (`dashboard/`) displays build history, APFD trends, and time saved metrics

### Key Data Flows
- `test_history.db` → feature extraction → `full_features.parquet` → model training → MLflow Registry
- GitHub push event → GitHub Action → FastAPI `/predict` → ranked test list → Maven execution → outcome feedback

### Feature Groups (25+ features)
- **Commit**: files changed, lines added/deleted, merge commit flag, commit hour/day
- **Author**: failure rate in 90-day window
- **Test history**: last outcome, failure rates (7d/30d/90d), days since last failure
- **Code ownership**: derived from commit history

### Evaluation
- APFD formula: `1 - (Σ rank_i / (n_tests × n_faults)) + (1 / (2n_tests))`
- Baselines to beat: Random, Alphabetical, Most Recently Failed
- Cross-validation: 5-fold `TimeSeriesSplit` (no data leakage from future → past)
- Statistical significance: Wilcoxon signed-rank test

## Planned Directory Structure

```
data/
  repos/        # cloned Java repos (gitignored)
  features/     # generated parquet files (gitignored)
scripts/        # standalone pipeline scripts (extract, tune, cross_validate)
src/
  features/     # commit_extractor.py, test_history_extractor.py, etc.
  models/       # xgboost_trainer.py, lgbm_trainer.py
  evaluation/   # apfd.py, strategies.py, splitter.py, flaky_detector.py
  serving/      # FastAPI app.py, schemas.py
notebooks/      # EDA and validation (01_ground_truth_validation.ipynb, etc.)
tests/          # pytest unit tests mirroring src/ structure
github-action/  # action.yml, scripts/discover_tests.sh
dashboard/      # ReactJS + Vite frontend
docs/
  literature/   # rocket-notes.md, supporting-notes.md, references.bib
  results/      # evaluation tables, plots
  sprint-*-backlog.md
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| xgboost | 2.0.3 | Primary ML model |
| lightgbm | 4.3.0 | Alternative ML model |
| scikit-learn | 1.4.2 | Pipelines, metrics, CV |
| optuna | 3.6.1 | Hyperparameter search |
| mlflow | 2.12.1 | Experiment tracking, model registry |
| fastapi | 0.111.0 | Prediction service |
| gitpython | 3.1.43 | Commit history traversal |
| javalang | 0.13.0 | Java AST parsing |
| evidently | 0.4.22 | Drift detection (PSI) |
| shap | 0.44.1 | Feature importance explainability |

MLflow backend: SQLite (local dev) with artifacts stored in `mlflow-artifacts/` (gitignored).

The `docker-compose.yml` spec is defined in `docs/sprint-1-backlog.md` (S1-02) and uses `ghcr.io/mlflow/mlflow:v2.12.1`.
