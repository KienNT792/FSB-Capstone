# Architecture Snapshot

Last updated: 2026-06-02

## System Boundary

AdaptCI uses RTPTorrent CSV data as the historical CI ground truth for Java test prioritization. It does not replay Maven builds to create labels. Current Sprint 1 work is foundation/data oriented: environment, RTPTorrent project selection, SQLite loading, validation notebook, and package scaffolding.

## Components

| Component | Tech | Location | Current status |
|-----------|------|----------|----------------|
| RTPTorrent source data | CSV | `data/repos/rtp-torrent/` | Present; source data, preserve in place |
| Project selector | Python, pandas | `data/scripts/select_rtp_projects.py` | Implemented; writes `data/rtp-project-summary.md` |
| SQLite loader | Python, sqlite3 | `data/scripts/load_rtp_dataset.py` | Implemented; writes gitignored `data/test_history.db` |
| Ground-truth validation | Jupyter, pandas, sqlite3 | `notebooks/01_ground_truth_validation.ipynb` | Present and has executed outputs |
| Feature pipeline | Python | `scripts/data_pipeline.py` | Placeholder (`pass`) |
| Feature/model/eval/serving packages | Python | `src/features/`, `src/models/`, `src/evaluation/`, `src/serving/` | Package skeletons only |
| MLflow tracking | Docker Compose, MLflow SQLite backend | `docker-compose.yml` | Configured for local server on port `5000` |
| Tests | pytest | `tests/` | Skeleton only |

## Data Flow

1. Read RTPTorrent project CSVs from `data/repos/rtp-torrent/<owner>@<repo>/`.
2. Run `data/scripts/select_rtp_projects.py` to summarize projects and mark selected candidates in `data/rtp-project-summary.md`.
3. Run `data/scripts/load_rtp_dataset.py` to load selected/manual projects into `data/test_history.db`.
4. Loader creates `test_runs` and `file_changes`.
5. `commit_sha` is mapped from RTPTorrent job-to-commit metadata where available.
6. `timestamp` remains `NULL` in Sprint 1; `job_sequence` is the current temporal-order fallback.
7. Future feature extraction should read from SQLite and write generated parquet artifacts under `data/features/`.

## SQLite Shape

Current local `data/test_history.db` exists and is large (`~7.49 GB`, generated and gitignored). Confirmed tables:

- `test_runs`
- `file_changes`
- `sqlite_sequence`

Important `test_runs` columns from the loader:

- `repo`, `job_id`, `commit_sha`, `test_id`
- `outcome`, `duration_ms`
- `timestamp`, `job_sequence`

Important `file_changes` columns:

- `repo`, `commit_sha`, `file_path`

## Current Project Selection

Current selected projects in `data/rtp-project-summary.md`:

- `l0rdn1kk0n@wicket-bootstrap`
- `deeplearning4j@deeplearning4j`
- `neuland@jade4j`
- `adamfisk@LittleProxy`
- `thinkaurelius@titan`

The current decision is a `>= 1%` failure-rate threshold with a 5-project limit. Some older backlog/plan acceptance text still mentions `>= 2%` or exactly 3 projects; treat that as stale unless explicitly revising Sprint 1 scope.

## Generated Artifacts

Do not commit these:

- `data/repos/rtp-torrent/`
- `data/features/`
- `data/test_history.db`
- `data/test_history.db-*`
- `mlflow-artifacts/`
- `mlflow-db/`

## Open Architecture Work

- Implement `scripts/data_pipeline.py`.
- Add real modules under `src/features/`, `src/models/`, `src/evaluation/`, and `src/serving/`.
- Add tests beyond package skeletons.
- Add timestamp enrichment in Sprint 2 before temporal feature work depends on commit dates.
- Verify loader `--auto` selection behavior before relying on DB contents for final experiments.
