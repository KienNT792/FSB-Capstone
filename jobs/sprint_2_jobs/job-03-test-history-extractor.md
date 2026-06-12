---
# Job 03: TestHistoryFeatureExtractor

## Objective
Implement `TestHistoryFeatureExtractor` at `src/features/test_history_extractor.py` with method `extract(test_id: str, as_of_ts: int, history_df: pd.DataFrame) -> dict` that returns 10 rolling per-test statistics using only records strictly before `as_of_ts`. The class must handle the cold-start case (no prior history) with defined sentinel values and must not raise on any valid input.

## Sprint Goal Alignment
This job produces the 10 test-level historical features (`last_outcome`, `failure_rate_7d/30d/90d`, `days_since_last_fail`, etc.) that are the primary signal for the Most Recently Failed (MRF) baseline and for the ML models. job-05 (FeatureJoiner) calls `extract()` once per `(commit, test)` pair, passing `as_of_ts` as the commit's Unix timestamp.

## Dependencies
- Upstream:
  - job-00: `timestamp` populated in `test_runs` (primary path); `job_sequence` available as fallback for NULL-timestamp rows (already populated by loader)
  - `data/test_history.db` with `test_runs` table (Sprint 1 deliverable)
- Downstream: job-05 (FeatureJoiner assembles test-history feature block alongside commit and author blocks), job-09 (unit tests)

## Scope (in)
- Class `TestHistoryFeatureExtractor` at `src/features/test_history_extractor.py`
- Method `extract(test_id: str, as_of_ts: int, history_df: pd.DataFrame) -> dict`
- `history_df` is a pre-loaded DataFrame (loaded once by FeatureJoiner, passed in) with columns from `test_runs`: `[test_id, outcome, timestamp, job_id, duration_ms]`
- `as_of_ts` is Unix epoch integer; filter to rows where `timestamp < as_of_ts` (strict less-than)
- For rows with `timestamp IS NULL`: substitute the job-order-derived pseudo-timestamp (computed during loading, available as a column — verify column name in `test_history.db` schema)
- Returns all 10 features:

| Feature | Type | Cold-start value | Description |
|---|---|---|---|
| `last_outcome` | int | -1 | 1 = last run FAIL, 0 = PASS/other |
| `failure_rate_7d` | float | -1 | FAIL / total in past 7 days |
| `failure_rate_30d` | float | -1 | FAIL / total in past 30 days |
| `failure_rate_90d` | float | -1 | FAIL / total in past 90 days |
| `days_since_last_fail` | float | 999 | Days since last FAIL |
| `days_since_last_run` | float | 999 | Days since last run of any outcome |
| `consecutive_passes` | int | 0 | Consecutive PASS count before `as_of_ts` |
| `avg_duration_ms` | float | 0 | Mean duration over last 20 runs |
| `duration_variance` | float | 0 | Variance of duration over last 20 runs; 0 if < 2 records |
| `run_count_30d` | int | 0 | Number of executions in past 30 days |

- Cold start (no prior history at all): return sentinel row as shown above
- Unit tests: cold start, only failures, only passes, mixed history, time boundary exactness (a record at exactly `as_of_ts` must NOT be included), `duration_variance` with < 2 records

## Out of Scope
- Author history features — job-02
- Commit-level churn features — job-01
- `feature_source` column — job-02 / job-05
- Writing to DuckDB or Parquet — job-05
- Dependency/import overlap — job-04

## Implementation Notes
**Window computations:**
- 7d window: `as_of_ts - 7*86400` to `as_of_ts` (exclusive)
- 30d window: `as_of_ts - 30*86400` to `as_of_ts`
- 90d window: `as_of_ts - 90*86400` to `as_of_ts`
- Failure rate `-1` when the window has zero records (not when it has zero failures — zero failures on N records is `0.0`, not `-1`)

**`last_outcome` and `consecutive_passes`:**
- Sort filtered history by `timestamp` descending (or `job_id` descending if timestamp NULL).
- `last_outcome`: outcome of the most recent row (1 if FAIL, 0 otherwise).
- `consecutive_passes`: count of leading PASS rows from most-recent backward; stop at first non-PASS.

**`avg_duration_ms` and `duration_variance`:**
- Use last 20 runs (most recent by timestamp/job_id), not the full 90d window.
- `duration_variance = 0` if fewer than 2 records in the last 20 runs.
- `avg_duration_ms = 0` if no records.

**Pseudo-timestamp for NULL rows:** verify the column name used in `test_history.db` for the job-order-derived ordering value. It may be `job_sequence` or another column name — read the actual schema with `duckdb.connect('data/test_history.db').execute("DESCRIBE test_runs").df()` before implementing.

**Performance:** `history_df` is pre-loaded and filtered per `test_id` by the caller (FeatureJoiner). This method should not query DuckDB directly — it operates purely on the passed DataFrame slice.

**Outcome encoding:** RTPTorrent outcome column contains string values (`'FAIL'`, `'PASS'`, `'SKIPPED'`, `'ERROR'`). Treat `'FAIL'` and `'ERROR'` as failure (value 1); all others as pass (value 0). Verify actual distinct values in `test_runs.outcome` before coding.

## Deliverables
- `src/features/test_history_extractor.py`
- `tests/test_test_history_extractor.py` (≥ 10 test cases)

## Verification
```bash
pytest tests/test_test_history_extractor.py -v
```
≥ 10 cases all pass. Boundary exactness test confirms `as_of_ts`-equal records are excluded.

## Definition of Done
- [ ] `TestHistoryFeatureExtractor` class exists at `src/features/test_history_extractor.py`
- [ ] `extract()` returns dict with all 10 features + correct cold-start sentinel values
- [ ] `timestamp < as_of_ts` (strict) filtering verified by unit test
- [ ] NULL-timestamp rows handled via pseudo-timestamp fallback
- [ ] `failure_rate_*d` returns `-1` when window has zero records (not zero failures)
- [ ] `duration_variance = 0` when fewer than 2 records
- [ ] Cold-start case produces: `last_outcome=-1`, all rates=-1, `days_since_last_fail=999`, `days_since_last_run=999`, counts=0
- [ ] `pytest tests/test_test_history_extractor.py` passes with ≥ 10 test cases
- [ ] No test accesses `data/test_history.db` directly
---
