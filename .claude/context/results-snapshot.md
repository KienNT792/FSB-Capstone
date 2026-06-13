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

## Sprint 2 Feature Pipeline Results (M1 closed 2026-06-13)

Feature Parquet artifacts have been generated for all 5 projects (`data/features/<project>_features.parquet` + `full_features.parquet`). Combined: 160,454 rows × 37 cols (31 feature columns).

Top-5 features by mutual information:

| Rank | Feature | MI Score |
|---|---|---|
| 1 | `days_since_last_fail` | 0.2365 |
| 2 | `failure_rate_90d` | 0.2002 |
| 3 | `failure_rate_30d` | 0.1888 |
| 4 | `consecutive_passes` | 0.1622 |
| 5 | `failure_rate_7d` | 0.1558 |

All top-5 are test-history features. No data leakage detected. Feature pipeline frozen from Sprint 3 onward.

## Next Result Milestones (Sprint 3)

- Implement `APFDCalculator` in `src/evaluation/apfd.py`.
- Implement `temporal_split` in `src/evaluation/splitter.py` (split by `commit_sha`).
- Implement 5 baseline strategies in `src/evaluation/strategies.py`.
- Run baseline eval: log 25 MLflow runs (5 strategies × 5 projects) to experiment `baseline`.
- Train XGBoost with Optuna tuning (≥50 trials); verify APFD > MRF on ≥1 project.
- Generate SHAP summary plot and top-10 feature importance table.
