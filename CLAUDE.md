# CLAUDE.md

<!-- maintainer: this file is the primary project memory for Claude Code.
Keep it under 200 lines. Architecture detail lives in .claude/context/.
Design decisions live in .claude/context/decisions-log.md. -->

## Project Status

**Current phase: Sprint 1 (Planning complete — implementation not yet started)**
No `src/`, `scripts/`, `tests/`, or `dashboard/` directories exist yet.
All commands below are **planned**, not runnable until the sprint they belong to is implemented.

See `docs/backlog/` for sprint-by-sprint implementation tasks.
See `.claude/context/architecture-snapshot.md` for system design details.
See `.claude/context/decisions-log.md` for key design decisions and rationale.

---

## What This Project Is

**AdaptCI** — an ML-based test prioritization system for Java/Maven CI pipelines.

- Ranks test execution order so the most likely failing tests run first (fail-fast)
- Reduces CI feedback latency; primary metric is **APFD** (Average Percentage of Faults Detected)
- Dataset: **RTPTorrent** (Mattis et al., MSR '20) — pre-collected TravisCI build logs for 20 Java projects
- Models: XGBoost and LightGBM, trained offline, served via FastAPI, integrated via GitHub Actions

**NOT**: a tool that re-runs `mvn test` to collect data. RTPTorrent CSVs are the ground truth source.

---

## Repository Layout (Current)

```
FSB-Capstone/
├── CLAUDE.md                    # ← you are here
├── README.md
├── .claude/
│   ├── settings.local.json
│   ├── commands/                # custom slash commands (invoke with /)
│   │   ├── debug-results.md     # /debug-results — diagnose unexpected model outputs
│   │   ├── experiment-plan.md   # /experiment-plan — generate ablation/eval plan
│   │   ├── sprint-review.md     # /sprint-review — review sprint backlog status
│   │   ├── thesis-review.md     # /thesis-review — review thesis draft section
│   │   └── write-section.md     # /write-section — draft a thesis chapter section
│   └── context/                 # persistent design context (read before making decisions)
│       ├── architecture-snapshot.md
│       ├── decisions-log.md
│       └── results-snapshot.md
├── docs/
│   ├── backlog/                 # sprint-1 through sprint-8 backlogs
│   ├── plan/
│   │   └── sprint-1-plan.md
│   └── reports/
│       └── MSE_Thesis_Proposal.docx
└── .gitignore
```

## Planned Layout (Sprint 1+, not yet created)

```
data/
  repos/         # cloned Java repos — gitignored
  features/      # generated parquet files — gitignored
scripts/         # standalone pipeline scripts
src/
  features/      # extractor modules
  models/        # trainer modules
  serving/       # FastAPI app
  evaluation/    # APFD, metrics, splitter
notebooks/       # EDA and validation
tests/           # pytest, mirrors src/ structure
github-action/   # GitHub Actions custom action
dashboard/       # ReactJS + Vite frontend
```

---

## Commands

### Environment (Sprint 1 — not yet runnable)
```bash
pyenv local 3.11
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### MLflow (Sprint 1 — not yet runnable)
```bash
docker compose up -d            # MLflow UI at http://localhost:5000
docker compose down
```

### Data pipeline (Sprint 1–2 — not yet runnable)
```bash
python scripts/load_rtptorrent.py --data-dir data/rtp-torrent-v11 --limit 20000
python scripts/data_pipeline.py                 # → data/features/full_features.parquet
```

### Model training (Sprint 3–4 — not yet runnable)
```bash
python scripts/tune_xgboost.py                  # 50 Optuna trials → MLflow
python scripts/tune_lgbm.py
python scripts/cross_validate.py                # 5-fold TimeSeriesSplit
```

### Serving (Sprint 5 — not yet runnable)
```bash
uvicorn src.serving.app:app --host 0.0.0.0 --port 8000
```

### Tests (Sprint 1+ — add tests as code is implemented)
```bash
pytest tests/                                   # full suite
pytest -v tests/test_apfd.py                    # single file
```

---

## Rules

- IMPORTANT: Never create or modify files in `data/repos/` or `data/features/` — these are gitignored generated artifacts.
- IMPORTANT: Always use `TimeSeriesSplit` for cross-validation — never `KFold` or random split (data leakage risk).
- IMPORTANT: Read `.claude/context/decisions-log.md` before proposing architecture changes.
- Do not use `javalang` as a hard dependency — wrap all AST parsing in `try/except` (Java 8/11 era repos have ~5% parse failure rate).
- All Python code: type hints required, no `import *`.
- Evaluation metric: APFD. Formula: `1 - (Σ rank_i / (n_tests × n_faults)) + (1 / (2n_tests))`.
- Baselines must include: Random, Alphabetical, Most Recently Failed — any ML result is only meaningful relative to these.
- Dataset is RTPTorrent CSVs at `data/rtp-torrent-v11/` — not Apache Commons clones.

---

## Key Dependencies (planned `requirements.txt`)

| Package       | Version | Purpose                          |
|---------------|---------|----------------------------------|
| xgboost       | 2.0.3   | Primary ML model                 |
| lightgbm      | 4.3.0   | Alternative ML model             |
| scikit-learn  | 1.4.2   | Pipelines, metrics, CV           |
| optuna        | 3.6.1   | Hyperparameter search            |
| mlflow        | 2.12.1  | Experiment tracking, registry    |
| fastapi       | 0.111.0 | Prediction service               |
| gitpython     | 3.1.43  | Commit metadata extraction       |
| javalang      | 0.13.0  | Java AST parsing (optional)      |
| evidently     | 0.4.22  | PSI-based drift detection        |
| shap          | 0.44.1  | Feature importance               |
| pandas        | 2.2.2   | Data manipulation                |
| pyarrow       | 16.0.0  | Parquet I/O                      |
| pytest        | 8.2.0   | Testing                          |

MLflow backend: SQLite (local dev). Artifacts in `mlflow-artifacts/` (gitignored).

---

## Custom Slash Commands

Use these by typing `/command-name` in Claude Code:

| Command            | When to use                                                  |
|--------------------|--------------------------------------------------------------|
| `/sprint-review`   | Review current sprint backlog and task status                |
| `/thesis-review`   | Evaluate a thesis section draft (structure, rigor, clarity)  |
| `/write-section`   | Draft or rewrite a thesis chapter section                    |
| `/experiment-plan` | Design ablation study or evaluation plan                     |
| `/debug-results`   | Diagnose unexpected model results or metric anomalies        |