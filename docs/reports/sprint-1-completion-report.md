# Sprint 1 Completion Report - Environment & Ground Truth

Date: 2026-06-12  
Database: `data/test_history.db` (DuckDB)  
Dataset: `data/repos/rtp-torrent`  
Status: Complete for Sprint 1 data rebuild; timestamp population deferred until local Git clones are available.

## Executive Summary

Sprint 1 was rebuilt after migrating the test-history store from SQLite to DuckDB while keeping the stable path `data/test_history.db`. The RTPTorrent source scan selected 5 projects, loaded 160,454 unique test-run records and 83,812 file-change records, and executed the validation notebook successfully.

The timestamp step was intentionally run in dry-run mode only. It currently reports `0.0%` coverage because the local Git clone root `data/git-repos` does not contain the selected repositories yet.

## Completed Artifacts

| Artifact | Result |
|----------|--------|
| `requirements.txt` install | Completed in `.venv`; all requirements already satisfied |
| `data/rtp-project-summary.md` | Updated with selection criteria, selected projects, DuckDB validation metrics, and timestamp dry-run status |
| `data/test_history.db` | Rebuilt as DuckDB with `test_runs` and `file_changes` |
| `notebooks/01_ground_truth_validation.ipynb` | Executed in-place against DuckDB |
| `scripts/run_sprint1.ps1` | Updated to use DuckDB runtime checks and smoke summary |
| `tests/` | `8 passed` |

## Selected Projects

| Project | Source Builds | Source Rows | Source Failure Rate | Loaded test_runs | Loaded Fail Rate | file_changes |
|---------|---------------:|------------:|--------------------:|-----------------:|-----------------:|-------------:|
| l0rdn1kk0n@wicket-bootstrap | 907 | 51,169 | 20.47% | 48,228 | 22.52% | 10,248 |
| deeplearning4j@deeplearning4j | 982 | 15,511 | 3.78% | 15,509 | 6.01% | 61,402 |
| neuland@jade4j | 931 | 35,887 | 2.91% | 35,887 | 3.69% | 3,135 |
| adamfisk@LittleProxy | 431 | 15,799 | 1.61% | 15,772 | 1.19% | 2,614 |
| thinkaurelius@titan | 941 | 49,998 | 1.25% | 45,058 | 1.46% | 6,413 |

## DuckDB Validation Results

| Metric | Result |
|--------|-------:|
| Total `test_runs` rows | 160,454 |
| Total `file_changes` rows | 83,812 |
| Rows with `duration_ms IS NULL` | 0 |
| Rows with `job_sequence IS NULL` | 0 |
| Rows with populated `timestamp` | 0 |

Per-project quality:

| Project | Null commit_sha | Null commit_sha % | Distinct Jobs | Distinct SHAs | Distinct Tests |
|---------|----------------:|------------------:|--------------:|--------------:|---------------:|
| adamfisk@LittleProxy | 4,798 | 30.42% | 581 | 262 | 52 |
| deeplearning4j@deeplearning4j | 884 | 5.70% | 1,038 | 871 | 174 |
| l0rdn1kk0n@wicket-bootstrap | 9,323 | 19.33% | 1,110 | 823 | 97 |
| neuland@jade4j | 36 | 0.10% | 932 | 314 | 46 |
| thinkaurelius@titan | 5,815 | 12.91% | 1,075 | 382 | 121 |

Outcome distribution:

| Project | PASS | FAIL | SKIPPED |
|---------|-----:|-----:|--------:|
| adamfisk@LittleProxy | 14,563 | 187 | 1,022 |
| deeplearning4j@deeplearning4j | 13,769 | 932 | 808 |
| l0rdn1kk0n@wicket-bootstrap | 36,648 | 10,860 | 720 |
| neuland@jade4j | 29,599 | 1,323 | 4,965 |
| thinkaurelius@titan | 44,398 | 660 | 0 |

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\run_sprint1.ps1 -InstallRequirements -AllowTimestampFailure
.\.venv\Scripts\python.exe -m jupyter nbconvert --execute --inplace notebooks\01_ground_truth_validation.ipynb
.\.venv\Scripts\python.exe -m pytest tests\
.\.venv\Scripts\python.exe scripts\add_timestamps.py --db-path data\test_history.db --git-root data\git-repos --auto --dry-run
```

Observed verification:

- Sprint 1 rebuild script completed and regenerated `data/rtp-project-summary.md` plus `data/test_history.db`.
- Unit tests completed with `8 passed`.
- Notebook execution completed and wrote updated outputs to `notebooks/01_ground_truth_validation.ipynb`.
- Timestamp dry-run completed without writing timestamps.

## Timestamp Dry-Run

| Project | Resolved SHAs | Timestamped Rows | Missing Repo SHAs | Status |
|---------|--------------:|-----------------:|------------------:|--------|
| adamfisk@LittleProxy | 0 / 262 | 0 / 10,974 | 262 | Deferred |
| deeplearning4j@deeplearning4j | 0 / 871 | 0 / 14,625 | 871 | Deferred |
| l0rdn1kk0n@wicket-bootstrap | 0 / 823 | 0 / 38,905 | 823 | Deferred |
| neuland@jade4j | 0 / 314 | 0 / 35,851 | 314 | Deferred |
| thinkaurelius@titan | 0 / 382 | 0 / 39,243 | 382 | Deferred |

Reason: the selected project Git clones are not present under `data/git-repos`.

## Notes And Follow-Up

- `data/test_history.db` remains the canonical Sprint 1 DuckDB artifact even though it keeps the `.db` extension.
- MLflow still uses its own SQLite backend in Docker Compose; that is separate from the DuckDB test-history database.
- `adamfisk@LittleProxy` has a high null `commit_sha` rate (`30.42%`) and should be treated carefully in timestamp-dependent analysis.
- Populate timestamps later by cloning selected repos under `data/git-repos/<owner>@<repo>` and rerunning `scripts/add_timestamps.py` without `--dry-run`.
