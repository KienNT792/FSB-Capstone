# Sprint 1 Completion Report - Environment, Ground Truth, and Timestamp Gate

Date: 2026-06-12  
Database: `data/test_history.db` (DuckDB)  
Dataset: `data/repos/rtp-torrent`  
Git clone root: `data/git-repos`  
Status: Complete. Sprint 1 data foundation is ready as the Sprint 2 reference baseline.

## Executive Summary

Sprint 1 established the AdaptCI data foundation using RTPTorrent as the source of real CI test history. The selected 5-project corpus has been loaded into DuckDB, validated, and timestamped from local Git commit metadata.

The final DuckDB artifact contains 160,454 unique `(repo, job_id, test_id)` records and 83,812 file-change records. All 2,652 distinct non-null commit SHAs resolve to timestamps across the 5 selected repositories. Rows with `commit_sha IS NULL` remain untimestamped by design because there is no commit identity to resolve.

## Completed Artifacts

| Artifact | Result |
|----------|--------|
| `.venv` | Recreated with Python 3.11.9; `requirements.txt` installed |
| `data/rtp-project-summary.md` | Updated with selected projects, loaded DB metrics, timestamp coverage, and Sprint 2 handoff notes |
| `data/test_history.db` | DuckDB database with `test_runs` and `file_changes` |
| `data/git-repos/<owner>@<repo>` | 5 selected repositories cloned for Git metadata resolution |
| `scripts/add_timestamps.py` | Optimized to resolve timestamps via batched Git CLI calls |
| `pytest.ini` | Added so pytest ignores cloned upstream repositories under `data/git-repos` |
| `notebooks/01_ground_truth_validation.ipynb` | Re-executed in place after timestamp update |
| `tests/` | Timestamp unit tests pass |

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
| Total `FAIL` rows | 13,962 |
| Rows with `commit_sha IS NULL` | 20,856 |
| Rows with `duration_ms IS NULL` | 0 |
| Rows with `job_sequence IS NULL` | 0 |
| Rows with populated `timestamp` | 139,598 |
| Overall timestamp row coverage | 87.00% |
| Timestamp coverage where `commit_sha IS NOT NULL` | 100.00% |
| Distinct non-null SHAs | 2,652 |
| Timestamped distinct SHAs | 2,652 |

Per-project quality:

| Project | Null commit_sha | Null commit_sha % | Timestamped Rows | Timestamp Row Coverage | Distinct SHAs | Timestamped SHAs | Date Range |
|---------|----------------:|------------------:|-----------------:|-----------------------:|--------------:|-----------------:|------------|
| adamfisk@LittleProxy | 4,798 | 30.42% | 10,974 | 69.58% | 262 | 262 | 2012-03-16 to 2016-08-07 |
| deeplearning4j@deeplearning4j | 884 | 5.70% | 14,625 | 94.30% | 871 | 871 | 2014-02-15 to 2016-02-13 |
| l0rdn1kk0n@wicket-bootstrap | 9,323 | 19.33% | 38,905 | 80.67% | 823 | 823 | 2013-03-31 to 2016-08-28 |
| neuland@jade4j | 36 | 0.10% | 35,851 | 99.90% | 314 | 314 | 2012-04-17 to 2016-07-04 |
| thinkaurelius@titan | 5,815 | 12.91% | 39,243 | 87.09% | 382 | 382 | 2012-06-07 to 2014-07-07 |

Outcome distribution:

| Project | PASS | FAIL | SKIPPED |
|---------|-----:|-----:|--------:|
| adamfisk@LittleProxy | 14,563 | 187 | 1,022 |
| deeplearning4j@deeplearning4j | 13,769 | 932 | 808 |
| l0rdn1kk0n@wicket-bootstrap | 36,648 | 10,860 | 720 |
| neuland@jade4j | 29,599 | 1,323 | 4,965 |
| thinkaurelius@titan | 44,398 | 660 | 0 |

## Timestamp Resolution

The original timestamp approach used GitPython commit lookup per SHA, which was too slow for large repositories. The final implementation uses:

1. `git log --all --format=%H %ct` to resolve reachable commits in one call.
2. `git show --no-patch --format=%H %ct` as a fallback for orphaned commit objects that exist in blobless clones but are not reachable from refs.
3. Batches of 200 SHAs per `git show` call to stay below the Windows command-line length limit.

Timestamp gate result:

| Project | Resolved SHAs | Eligible Rows | Timestamped Rows | Status |
|---------|--------------:|--------------:|-----------------:|--------|
| adamfisk@LittleProxy | 262 / 262 | 10,974 | 10,974 | PASS |
| deeplearning4j@deeplearning4j | 871 / 871 | 14,625 | 14,625 | PASS |
| l0rdn1kk0n@wicket-bootstrap | 823 / 823 | 38,905 | 38,905 | PASS |
| neuland@jade4j | 314 / 314 | 35,851 | 35,851 | PASS |
| thinkaurelius@titan | 382 / 382 | 39,243 | 39,243 | PASS |

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\add_timestamps.py --db-path data\test_history.db --git-root data\git-repos --auto --dry-run
.\.venv\Scripts\python.exe -m pytest -q
```

Observed verification:

- Timestamp dry-run completed with 5/5 projects passing at 100% distinct-SHA coverage.
- Unit tests completed with `8 passed`.
- Validation notebook re-executed in place against the timestamped DuckDB artifact.
- `pytest.ini` prevents accidental collection of upstream tests from cloned repositories.

## Sprint 2 Handoff

Sprint 2 can now start from a real, timestamped dataset. The next required engineering work is feature generation:

- Implement `scripts/data_pipeline.py`.
- Implement feature modules under `src/features/`.
- Write generated Parquet artifacts under `data/features/`.
- Validate temporal ordering and leakage before training.
- Use `job_sequence` as fallback only for rows where `commit_sha IS NULL` and `timestamp` cannot be resolved.

Important caveats:

- `adamfisk@LittleProxy` and `thinkaurelius@titan` have low failure rates and should be reported with high-variance caveats.
- `adamfisk@LittleProxy` has the highest null `commit_sha` rate (`30.42%`), so timestamp-dependent analysis should explicitly track filtering or fallback behavior for this project.
- `scripts/data_pipeline.py` is currently a placeholder and will not produce feature artifacts until Sprint 2 implementation is added.
