# Architecture Snapshot

Last updated: 2026-06-12

## System Boundary

AdaptCI uses RTPTorrent CSV data as the historical CI ground truth for Java test prioritization. It does not replay Maven builds to create labels. Sprint 1 is complete: selected RTPTorrent projects are loaded into DuckDB, local Git clones are available, and commit timestamps are populated for every non-null commit SHA.

## Components

| Component | Tech | Location | Current status |
|-----------|------|----------|----------------|
| RTPTorrent source data | CSV | `data/repos/rtp-torrent/` | Present; source data, preserve in place |
| Local Git metadata clones | Git | `data/git-repos/<owner>@<repo>/` | Present for all 5 selected projects; generated and gitignored |
| Project selector | Python, pandas | `data/scripts/select_rtp_projects.py` | Implemented; writes `data/rtp-project-summary.md` |
| DuckDB loader | Python, duckdb | `data/scripts/load_rtp_dataset.py` | Implemented; writes gitignored `data/test_history.db` |
| Timestamp enricher | Python, git CLI, duckdb | `scripts/add_timestamps.py` | Implemented; 5/5 selected projects pass timestamp gate |
| Ground-truth validation | Jupyter, pandas, duckdb | `notebooks/01_ground_truth_validation.ipynb` | Present; rerun after timestamp update before thesis use |
| Feature pipeline | Python | `scripts/data_pipeline.py` | Placeholder (`pass`) |
| Feature/model/eval/serving packages | Python | `src/features/`, `src/models/`, `src/evaluation/`, `src/serving/` | Package skeletons only |
| MLflow tracking | Docker Compose, MLflow SQLite backend | `docker-compose.yml` | Configured for local server on port `5000` |
| Tests | pytest | `tests/`, `pytest.ini` | Timestamp tests pass; pytest ignores cloned upstream repos |

## Data Flow

1. Read RTPTorrent project CSVs from `data/repos/rtp-torrent/<owner>@<repo>/`.
2. Run `data/scripts/select_rtp_projects.py` to summarize projects and mark selected candidates in `data/rtp-project-summary.md`.
3. Run `data/scripts/load_rtp_dataset.py` to load selected/manual projects into `data/test_history.db`.
4. Loader creates `test_runs` and `file_changes`.
5. `commit_sha` is mapped from RTPTorrent job-to-commit metadata where available.
6. Run `scripts/add_timestamps.py` against `data/git-repos` to populate `timestamp` from commit metadata.
7. Future feature extraction should read from DuckDB and write generated parquet artifacts under `data/features/`.

## DuckDB Schema

Current local `data/test_history.db` exists and is generated/gitignored. Confirmed tables:

- `test_runs`
- `file_changes`

Important `test_runs` columns:

- `repo`, `job_id`, `commit_sha`, `test_id`
- `outcome`, `duration_ms`
- `timestamp`, `job_sequence`

Important `file_changes` columns:

- `repo`, `commit_sha`, `file_path`

## Current Project Selection

Current selected projects in `data/rtp-project-summary.md`:

- `adamfisk@LittleProxy`
- `deeplearning4j@deeplearning4j`
- `l0rdn1kk0n@wicket-bootstrap`
- `neuland@jade4j`
- `thinkaurelius@titan`

The current decision is a `>= 1%` failure-rate threshold with a 5-project limit. Some older backlog/plan acceptance text still mentions `>= 2%` or exactly 3 projects; treat that as stale unless explicitly revising Sprint 1 scope.

## Current Data Metrics

- `test_runs`: 160,454
- `file_changes`: 83,812
- `FAIL` rows: 13,962
- `commit_sha IS NULL`: 20,856
- `timestamp IS NOT NULL`: 139,598
- Distinct non-null SHAs: 2,652
- Timestamped distinct SHAs: 2,652
- Timestamp coverage for rows with `commit_sha`: 100%

## Generated Artifacts

Do not commit these:

- `data/repos/rtp-torrent/`
- `data/git-repos/`
- `data/features/`
- `data/test_history.db`
- `data/test_history.db-*`
- `mlflow-artifacts/`
- `mlflow-db/`

## Open Architecture Work

- Implement `scripts/data_pipeline.py`.
- Add real modules under `src/features/`, `src/models/`, `src/evaluation/`, and `src/serving/`.
- Add Sprint 2 tests for feature extractors and feature joins.
- Rerun/update `notebooks/01_ground_truth_validation.ipynb` if notebook outputs are used as the canonical written validation.
- Preserve temporal safety: split by commit groups and avoid using future test history when generating features.
