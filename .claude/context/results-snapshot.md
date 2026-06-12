# Experimental Results Snapshot

Last updated: 2026-06-12

## Status

No model-training, APFD, baseline APFD, cross-validation, or serving results exist yet. Current results are Sprint 1 data-selection, DuckDB validation, and timestamp coverage only.

## Project Selection Snapshot

`data/rtp-project-summary.md` marks these 5 projects as selected:

| Project | Builds | Source tests | Source failure rate |
|---------|-------:|-------------:|--------------------:|
| `adamfisk@LittleProxy` | 431 | 15,799 | 1.61% |
| `deeplearning4j@deeplearning4j` | 982 | 15,511 | 3.78% |
| `l0rdn1kk0n@wicket-bootstrap` | 907 | 51,169 | 20.47% |
| `neuland@jade4j` | 931 | 35,887 | 2.91% |
| `thinkaurelius@titan` | 941 | 49,998 | 1.25% |

Current selection threshold is `>= 1%`, not `>= 2%`.

## DuckDB Validation Snapshot

Current local `data/test_history.db` contains only the 5 selected projects. `notebooks/01_ground_truth_validation.ipynb` has been re-executed against this timestamped artifact.

- Total `test_runs`: 160,454
- Total `file_changes`: 83,812
- Total `FAIL` rows: 13,962
- Rows with `duration_ms IS NULL`: 0
- Rows with `job_sequence IS NULL`: 0
- Rows with `timestamp IS NOT NULL`: 139,598
- Distinct non-null SHAs: 2,652
- Timestamped distinct SHAs: 2,652

Per-project quality:

| Project | Loaded rows | Failure rate | Null `commit_sha` rate | Timestamp row coverage | SHA timestamp coverage |
|---------|------------:|-------------:|------------------------:|-----------------------:|-----------------------:|
| `adamfisk@LittleProxy` | 15,772 | 1.19% | 30.42% | 69.58% | 100.00% |
| `deeplearning4j@deeplearning4j` | 15,509 | 6.01% | 5.70% | 94.30% | 100.00% |
| `l0rdn1kk0n@wicket-bootstrap` | 48,228 | 22.52% | 19.33% | 80.67% | 100.00% |
| `neuland@jade4j` | 35,887 | 3.69% | 0.10% | 99.90% | 100.00% |
| `thinkaurelius@titan` | 45,058 | 1.46% | 12.91% | 87.09% | 100.00% |

Rows without `timestamp` correspond to rows without `commit_sha`; they are dataset gaps, not timestamp resolution failures.

## Baseline/APFD Results

| Strategy | Status |
|----------|--------|
| Random | Not computed yet |
| Alphabetical | Not computed yet |
| Most Recently Failed | Not computed yet |
| XGBoost | Not trained yet |
| LightGBM | Not trained yet |

## Data Quality Notes

- Current local DuckDB database is generated and gitignored.
- Loader `--auto` selection now resolves exactly the 5 `SELECTED` rows from `data/rtp-project-summary.md`.
- `adamfisk@LittleProxy` has the highest null `commit_sha` rate (`30.42%`) and should be tracked carefully in timestamp-dependent analysis.
- `adamfisk@LittleProxy` and `thinkaurelius@titan` have low failure rates; report results with high-variance caveats.
- `timestamp` is a Unix epoch integer from Git commit metadata. Use `job_sequence` only as fallback for rows with no timestamp.

## Next Result Milestones

- Implement feature generation under `scripts/data_pipeline.py` and `src/features/`.
- Produce feature Parquet artifacts under `data/features/`.
- Validate temporal ordering and leakage before training.
- Compute APFD baselines: Random, Alphabetical, Most Recently Failed.
- Train/evaluate XGBoost and LightGBM against those baselines with temporal splits.
