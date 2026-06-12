# Experimental Results Snapshot

Last updated: 2026-06-02

## Status

No model-training, APFD, baseline APFD, cross-validation, or serving results exist yet. Current results are Sprint 1 data-selection and ground-truth validation only.

## Project Selection Snapshot

`data/rtp-project-summary.md` marks these 5 projects as selected:

| Project | Builds | Tests | Failure rate |
|---------|--------|-------|--------------|
| `l0rdn1kk0n@wicket-bootstrap` | 907 | 51,169 | 20.47% |
| `deeplearning4j@deeplearning4j` | 982 | 15,511 | 3.78% |
| `neuland@jade4j` | 931 | 35,887 | 2.91% |
| `adamfisk@LittleProxy` | 431 | 15,799 | 1.61% |
| `thinkaurelius@titan` | 941 | 49,998 | 1.25% |

Current selection threshold is `>= 1%`, not `>= 2%`.

## DuckDB Validation Snapshot

`notebooks/01_ground_truth_validation.ipynb` contains executed outputs against `data/test_history.db`:

- Total `test_runs`: `22,539,830`
- Selected-project quality from notebook output:

| Project | Failure rate | Null `commit_sha` rate | Notebook status using old `>= 2%` check |
|---------|--------------|------------------------|------------------------------------------|
| `adamfisk@LittleProxy` | 1.19% | 30.4% | FAIL under old 2% check |
| `deeplearning4j@deeplearning4j` | 6.01% | 5.7% | OK |
| `l0rdn1kk0n@wicket-bootstrap` | 22.52% | 19.3% | OK |
| `neuland@jade4j` | 3.69% | 0.1% | OK |
| `thinkaurelius@titan` | 1.46% | 12.9% | FAIL under old 2% check |

Interpret the old 2% notebook failure flags as stale relative to the current 1% decision.

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
- The DB appears to contain all 20 RTPTorrent projects, not only the 5 selected projects, based on notebook output. Verify/fix loader `--auto` selection before using DB contents for final selected-project experiments.
- Several non-selected repos have high null `commit_sha` rates in the notebook output; selected projects stay below 40%.
- `timestamp` is expected to be `NULL` in Sprint 1; use `job_sequence` for ordering until timestamp enrichment is implemented.

## Next Result Milestones

- Fix/verify selected-project-only loading.
- Implement feature generation under `scripts/data_pipeline.py` and `src/features/`.
- Compute APFD baselines: Random, Alphabetical, Most Recently Failed.
- Train/evaluate XGBoost and LightGBM against those baselines with temporal splits.
