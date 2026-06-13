# Architecture Snapshot

Last updated: 2026-06-13 (Sprint 2 / M1 closed)

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
| Feature pipeline | Python | `scripts/data_pipeline.py` | Implemented and validated; produces `<project>_features.parquet` for all 5 selected projects |
| Feature assembler | Python | `data/scripts/assemble_full_features.py` | Concatenates per-project parquets → `data/features/full_features.parquet` (160,454 × 37); runs `validate_features()` before write |
| Feature packages | Python | `src/features/` | Extractors implemented: `CommitFeatureExtractor`, `TestHistoryFeatureExtractor`, `DependencyFeatureExtractor`, `FeatureJoiner`, `validate_features()` |
| Model/eval/serving packages | Python | `src/models/`, `src/evaluation/`, `src/serving/` | Package skeletons only — pending Sprint 3+ |
| MLflow tracking | Docker Compose, MLflow SQLite backend | `docker-compose.yml` | Configured for local server on port `5000` |
| Tests | pytest | `tests/`, `pytest.ini` | Timestamp tests pass; pytest ignores cloned upstream repos |

## Data Flow

1. Read RTPTorrent project CSVs from `data/repos/rtp-torrent/<owner>@<repo>/`.
2. Run `data/scripts/select_rtp_projects.py` to summarize projects and mark selected candidates in `data/rtp-project-summary.md`.
3. Run `data/scripts/load_rtp_dataset.py` to load selected/manual projects into `data/test_history.db`.
4. Loader creates `test_runs` and `file_changes`.
5. `commit_sha` is mapped from RTPTorrent job-to-commit metadata where available.
6. Run `scripts/add_timestamps.py` against `data/git-repos` to populate `timestamp` from commit metadata.
7. `scripts/add_timestamps.py` resolves `timestamp` via batched Git CLI (`git log --all` plus batched `git show` fallback for unreachable objects in blobless clones) — NOT per-SHA GitPython lookups as originally planned. All 2,652 non-null `commit_sha` values across the 5 selected projects are now timestamped (100% SHA coverage, exceeds the 70% gate).
8. Run `scripts/data_pipeline.py --project <owner>@<repo>` for each selected project; reads from DuckDB and writes `data/features/<project>_features.parquet`. Validated end-to-end by `notebooks/02_eda_features.ipynb`.
9. Combined output: 160,454 rows × 37 columns (31 numeric feature columns) across all 5 projects; validation gate (`validate_features()`) passes for all projects.

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

## Sprint 2 Feature Pipeline — Output Summary

| Project | Shape | Failure rate | commit_meta_missing | commit_diff_missing |
|---------|-------|--------------|----------------------|----------------------|
| `adamfisk@LittleProxy` | (15772, 37) | 1.19% | 30.42% | 30.42% |
| `deeplearning4j@deeplearning4j` | (15509, 37) | 6.01% | 5.70% | 100.00% |
| `l0rdn1kk0n@wicket-bootstrap` | (48228, 37) | 22.52% | 19.53% | 19.53% |
| `neuland@jade4j` | (35887, 37) | 3.69% | 0.10% | 0.10% |
| `thinkaurelius@titan` | (45058, 37) | 1.46% | 12.91% | 12.91% |
| **Combined** | **(160454, 37)** | **8.70%** | — | — |

`deeplearning4j` `commit_diff_missing` of 100% is tracked as a pending decision in `docs/decisions-log.md` (2026-06-12 entry).

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
- `data/features/` (includes `full_features.parquet` and all per-project parquets)
- `data/test_history.db`
- `data/test_history.db-*`
- `mlflow-artifacts/`
- `mlflow-db/`

## Open Architecture Work (Sprint 3+)

- Add real modules under `src/models/`, `src/evaluation/`, and `src/serving/`.
- Implement `APFDCalculator` (`src/evaluation/apfd.py`), `temporal_split` (`src/evaluation/splitter.py`), and 5 baseline strategies (`src/evaluation/strategies.py`).
- Add tests for evaluation framework (APFD, splitter, strategies, runner).
- Rerun/update `notebooks/01_ground_truth_validation.ipynb` if notebook outputs are used as the canonical written validation.
- Preserve temporal safety: split by commit groups (`TimeSeriesSplit` per project, by `commit_sha`); do not leak future test history into feature rows.
- Pending: resolve `deeplearning4j` `commit_diff_missing=100%` — see decisions-log.md Pending table (default Option B if no trigger fires by end of Sprint 4).
