---
# Job 05: FeatureJoiner — Master DataFrame Assembly

## Objective
Implement `FeatureJoiner` at `src/features/feature_joiner.py` with method `build(repo: str, db_path: str) -> pd.DataFrame` that iterates over all `(commit, test)` pairs in `test_history.db` for the given project, calls each extractor once per appropriate granularity (commit-level features once per SHA, test-level features once per test per commit), and assembles the master feature DataFrame saved to `data/features/{repo_name}_features.parquet`. The output DataFrame is the direct input to job-07 (validation) and ultimately to Sprint 3 model training.

## Sprint Goal Alignment
This job is the integration hub — it wires together the four extractors from jobs 01–04 and produces `{repo}_features.parquet` under `data/features/`. It is what `data_pipeline.py` (job-06) calls as its primary step. Without this, no Parquet artifact exists and the sprint Definition of Done cannot be met.

## Dependencies
- Upstream:
  - job-01: `CommitFeatureExtractor.extract()` must exist and return commit-level feature dict
  - job-02: `CommitFeatureExtractor.extract_author_features()` must exist and return author dict with `feature_source`
  - job-03: `TestHistoryFeatureExtractor.extract()` must exist
  - job-04: `DependencyFeatureExtractor.extract()` must exist
  - job-00: `timestamp` populated in `test_runs` (required for time-aware filtering)
  - `data/test_history.db` with both `test_runs` and `file_changes` tables
- Downstream: job-06 (pipeline entrypoint calls `FeatureJoiner.build()`), job-07 (validates the output DataFrame), job-08 (EDA notebook loads the Parquet), job-09 (integration-style tests)

## Scope (in)
- Class `FeatureJoiner` at `src/features/feature_joiner.py`
- Method `build(repo: str, db_path: str) -> pd.DataFrame`
- Output: one row per `(commit_sha, test_id)` pair
- **Column set** (all features from jobs 01–04 plus metadata):
  - From job-01: `files_changed_total`, `java_files_changed`, `source_files_changed`, `test_files_changed`, `lines_added`, `lines_deleted`, `churn_total`, `is_merge_commit`, `commit_hour`, `commit_day_of_week`, `keyword_risk_score`, `commit_meta_missing`
  - From job-02: `author_commit_count_90d`, `author_failure_rate_90d`, `author_feature_fallback`, `feature_source`
  - From job-03: `last_outcome`, `failure_rate_7d`, `failure_rate_30d`, `failure_rate_90d`, `days_since_last_fail`, `days_since_last_run`, `consecutive_passes`, `avg_duration_ms`, `duration_variance`, `run_count_30d`
  - From job-04: `test_file_touched`, `import_overlap`, `same_package`, `changed_files_in_module`, `dependency_parse_failed`
  - Metadata: `commit_sha`, `test_id`, `label` (1=FAIL, 0=PASS/other), `timestamp`
  - Audit: `feature_source` (from job-02 — `'timestamp'` or `'job_sequence'`; excluded from model `X` matrix)
- **Excluded from model `X` matrix** (must NOT be passed to Sprint 3 trainers): `commit_sha`, `test_id`, `label`, `timestamp`, `feature_source`
- **Missing values strategy:**
  - Numeric cold-start sentinels (`-1`, `999`) are preserved as-is
  - NULL values that are NOT intentional sentinels raise `ValueError` during build (non-sentinel NULLs indicate a join bug)
- **Commit-batching:** for each unique `commit_sha`, compute commit-level features once and broadcast to all tests in that commit. Do not recompute per-test.
- Progress logging: `"Processing commit {i}/{n}: {sha[:8]}"` printed every 10 commits
- Output saved to `data/features/{repo_name}_features.parquet` (where `repo_name` is the `repo` parameter with `@` and `/` replaced by `_` or used as-is — document the exact naming convention)
- ≥ 4 integration-style unit tests in `tests/test_feature_joiner.py` using a small synthetic DuckDB

## Out of Scope
- CLI argument parsing — job-06 (`data_pipeline.py`)
- `validate_features()` call — job-07 (called by job-06 after `FeatureJoiner.build()` returns)
- EDA — job-08
- Hyperparameter tuning, model training — Sprint 3+

## Implementation Notes
**Processing order:**
1. Load all `test_runs` for `repo` into memory as `history_df` (once).
2. Load all `file_changes` for `repo` into memory as `changes_df` (once).
3. Get sorted unique commit SHAs (sort by `timestamp` or `job_sequence` as fallback).
4. For each commit SHA `sha`:
   a. Call `commit_extractor.extract(sha)` → commit feature dict (broadcast to all tests).
   b. Resolve `author_email` from git commit object (needed by `extract_author_features`).
   c. For each `test_id` that ran in this commit:
      - Call `commit_extractor.extract_author_features(sha, history_df)` → author dict
      - Call `test_history_extractor.extract(test_id, as_of_ts, history_df)` → test history dict
      - Call `dependency_extractor.extract(test_id, changed_java_files_for_sha, repo_path)` → dependency dict
      - Merge all dicts + `label` from `test_runs.outcome` + `timestamp` + `commit_sha` + `test_id`
      - Append to rows list.
5. Construct DataFrame from rows list.
6. Check for non-sentinel NULLs; raise `ValueError` if found.
7. Save to Parquet.

**`label` encoding:** `outcome == 'FAIL' OR outcome == 'ERROR'` → 1; else → 0. Verify exact distinct values from `test_runs`.

**`author_email` resolution:** call `git.Repo(repo_path).commit(sha).author.email`. If commit not found (commit_meta_missing=1), use empty string `""` for email — the author extractor will return cold-start values.

**`as_of_ts` for test history:** use the commit's `timestamp` (Unix epoch). For commits where `timestamp IS NULL`, use the commit's `job_sequence` value cast to a pseudo-Unix timestamp (e.g. `job_sequence * 86400` as a monotonic surrogate). Document this in a comment.

**`repo_name` file naming:** use the `repo` parameter as-is for the Parquet filename, e.g. `data/features/neuland@jade4j_features.parquet`. Avoid replacing `@` since it is already used in all project identifiers consistently.

**Synthetic DuckDB for tests:** create an in-memory DuckDB with 3 commits × 2 tests = 6 rows; assert output shape is `(6, ≥20)` and all expected columns are present.

## Deliverables
- `src/features/feature_joiner.py`
- `tests/test_feature_joiner.py` (≥ 4 integration-style tests with synthetic in-memory DuckDB)
- `data/features/{repo_name}_features.parquet` — produced by running `data_pipeline.py` (job-06), not by this job's tests

## Verification
```bash
# Unit tests
pytest tests/test_feature_joiner.py -v

# End-to-end smoke test (after job-06 is done)
python scripts/data_pipeline.py --project neuland@jade4j --db-path data/test_history.db \
  --rtp-path data/repos/rtp-torrent --output-path data/features/neuland@jade4j_features.parquet
# Expected final line: "Done. Shape: (N rows, ≥20 cols). Label distribution: {0: X, 1: Y}. commit_meta_missing: Z rows."
```

## Definition of Done
- [ ] `FeatureJoiner` class exists at `src/features/feature_joiner.py`
- [ ] `build()` returns DataFrame with one row per `(commit_sha, test_id)` pair
- [ ] Column set includes all features from jobs 01–04 + `label`, `timestamp`, `commit_sha`, `test_id`, `feature_source`
- [ ] Commit-level features computed once per SHA and broadcast to all tests in that commit
- [ ] Cold-start sentinels (`-1`, `999`) preserved; non-sentinel NULLs raise `ValueError`
- [ ] Progress logged every 10 commits
- [ ] Output saved to `data/features/{repo_name}_features.parquet`
- [ ] `feature_source` column present with only `{'timestamp', 'job_sequence'}` values
- [ ] `pytest tests/test_feature_joiner.py` passes with ≥ 4 integration-style tests
---
