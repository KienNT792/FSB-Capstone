# Sprint 2 Backlog — Full Feature Pipeline

**Duration:** Week 3–4  
**Sprint Goal:** `full_features.parquet` production-ready; end-to-end pipeline runs in a single command.  
**Phase:** Foundation & Data  
**Effort estimate:** ~60h

> **Dataset change (v2):** Feature extraction now operates on RTPTorrent CSV data loaded into SQLite (S1-06). Git repositories are cloned read-only for commit metadata and diff features. `javalang` is retained but optional. The `data_pipeline.py` entry point now takes `--project` (RTPTorrent project name) instead of `--repo-path`.

---

## Definition of Done

- [ ] `python scripts/data_pipeline.py --project apache@sling` produces `full_features.parquet` in ≤ 5 minutes
- [ ] Feature matrix contains ≥ 20 columns with no data leakage (time-awareness verified)
- [ ] All extractor classes covered by unit tests; `pytest tests/` passes 100%
- [ ] EDA notebook executed end-to-end with correlation heatmap and mutual information ranking

---

## Stories

---

### S2-01 · CommitFeatureExtractor — code churn features

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement the `CommitFeatureExtractor` class that derives file-level change metrics from a commit. File-list features are sourced primarily from the `file_changes` table (loaded from RTPTorrent `patches.csv`), which is faster than running a live git diff. Line-count features (added/deleted) are derived from gitpython diff against the cloned repo.

**Acceptance Criteria:**
- Class located at `src/features/commit_extractor.py`
- Constructor accepts a `git.Repo` object and a `db_path: str` (path to SQLite)
- Method `extract(commit_sha: str) -> dict` returns a flat dictionary
- **File-list features** (sourced from `file_changes` table — fast path):

| Feature | Type | Description |
|---------|------|-------------|
| `files_changed_total` | int | Total files in `file_changes` for this SHA |
| `java_files_changed` | int | `.java` files only |
| `source_files_changed` | int | `.java` files not under `test/` path |
| `test_files_changed` | int | `.java` files under `test/` path |

- **Commit metadata features** (sourced from gitpython — requires cloned repo):

| Feature | Type | Description |
|---------|------|-------------|
| `lines_added` | int | Total `+` lines across all changed files (git diff) |
| `lines_deleted` | int | Total `-` lines across all changed files (git diff) |
| `churn_total` | int | `lines_added + lines_deleted` |
| `is_merge_commit` | int | 1 if commit has > 1 parent, else 0 |
| `commit_hour` | int | Hour of `authored_datetime` (0–23) |
| `commit_day_of_week` | int | Weekday of `authored_datetime` (0=Mon) |
| `keyword_risk_score` | int | Count of risk keywords in commit message |

- If `commit_sha` is not found in the cloned repo (some RTPTorrent commits may be from forks), return zeros for metadata features with `commit_meta_missing=1` flag
- Risk keywords list: `["fix", "hotfix", "bug", "patch", "revert", "urgent", "crash", "error", "broken", "regression"]`
- Commits with no parents (initial commit) return zeros for diff-based features
- Unit tests in `tests/test_commit_extractor.py` cover: normal commit, merge commit, initial commit, commit not found in repo (meta missing), commit with no Java files

---

### S2-02 · CommitFeatureExtractor — author history features

**Priority:** High  
**Estimate:** 6h

**Description:**  
Extend `CommitFeatureExtractor` to compute per-author historical failure rate, using only commits that precede the current commit (time-aware).

**Acceptance Criteria:**
- Method `extract_author_features(commit_sha: str, history_df: pd.DataFrame) -> dict` added to `CommitFeatureExtractor`
- `history_df` is a DataFrame of past test runs (from `test_history.db`) with columns `[commit_sha, outcome, timestamp, author_email]`
- Returns:

| Feature | Type | Description |
|---------|------|-------------|
| `author_commit_count_90d` | int | Commits by this author in past 90 days |
| `author_failure_rate_90d` | float | Fraction of this author's commits that led to ≥ 1 test failure, past 90 days |

- Only commits with `timestamp < current_commit_timestamp` are included (no leakage)
- Authors with < 3 commits in window return `author_failure_rate_90d = -1` (unseen flag)
- Unit tests verify time-aware filtering: future commits must not influence the result

---

### S2-03 · TestHistoryFeatureExtractor

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Implement `TestHistoryFeatureExtractor` that derives per-test rolling statistics from past execution records. Source data is the `test_runs` table in SQLite, populated from RTPTorrent CSVs. For records where `timestamp` is NULL (unmapped SHA), fall back to ordering by `job_id` as a proxy for temporal ordering.

**Acceptance Criteria:**
- Class located at `src/features/test_history_extractor.py`
- Method `extract(test_id: str, as_of_ts: int, history_df: pd.DataFrame) -> dict`
- `as_of_ts` is a Unix epoch; only records with `timestamp < as_of_ts` are used (for records with NULL timestamp, substitute with a job-order-derived pseudo-timestamp computed during S1-06 loading)
- Returns:

| Feature | Type | Description |
|---------|------|-------------|
| `last_outcome` | int | 1 = last run FAIL, 0 = PASS, -1 = no history |
| `failure_rate_7d` | float | FAIL / total in past 7 days; -1 if no records |
| `failure_rate_30d` | float | FAIL / total in past 30 days; -1 if no records |
| `failure_rate_90d` | float | FAIL / total in past 90 days; -1 if no records |
| `days_since_last_fail` | float | Days since last FAIL; 999 if never failed |
| `days_since_last_run` | float | Days since last run of any outcome |
| `consecutive_passes` | int | Consecutive PASS count before `as_of_ts` |
| `avg_duration_ms` | float | Mean duration over last 20 runs; 0 if no data |
| `duration_variance` | float | Variance of duration over last 20 runs; 0 if < 2 records |
| `run_count_30d` | int | Number of executions in past 30 days |

- Tests with no history at all return the "cold start" row: `last_outcome=-1`, rates=-1, `days_since_last_fail=999`, counts=0
- Unit tests cover: cold start, only failures, only passes, mixed history, time boundary exactness

---

### S2-04 · DependencyFeatureExtractor

**Priority:** High  
**Estimate:** 8h

**Description:**  
Implement `DependencyFeatureExtractor` that estimates the coupling between a test file and the files changed in a commit, using import-level analysis via `javalang`. The changed file list is read from the `file_changes` table (from RTPTorrent `patches.csv`), and the test Java source is read from the cloned repository. RTPTorrent repos are Java 8/11 era, so `javalang` parse failure rate is expected to be low.

**Acceptance Criteria:**
- Class located at `src/features/dependency_extractor.py`
- Method `extract(test_id: str, changed_java_files: list[str], repo_path: str) -> dict`
- `test_id` maps to a `.java` file path (convention: `com.example.FooTest` → `src/test/java/com/example/FooTest.java`)
- `changed_java_files` sourced from `file_changes` table (no need for live git diff)
- Returns:

| Feature | Type | Description |
|---------|------|-------------|
| `test_file_touched` | int | 1 if the test file itself is in `changed_java_files` |
| `import_overlap` | int | Count of changed files whose class name appears in test file's import list |
| `same_package` | int | 1 if any changed source file shares the test's package |
| `changed_files_in_module` | int | Count of changed files in the same Maven module as the test |

- If test file cannot be located on disk (some commits may have deleted the file), return all zeros with flag `dependency_parse_failed=1`
- `javalang.parse.parse()` failures are caught; return zeros rather than raise
- Unit tests use a synthetic Java file fixture, not real repo files

---

### S2-05 · FeatureJoiner — master DataFrame assembly

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement `FeatureJoiner` that iterates over all `(commit, test)` pairs in `test_history.db`, calls each extractor, and assembles the master feature DataFrame.

**Acceptance Criteria:**
- Class located at `src/features/feature_joiner.py`
- Method `build(repo: str, db_path: str) -> pd.DataFrame`
- Output DataFrame has one row per `(commit_sha, test_id)` pair
- Columns: all features from S2-01 through S2-04 plus `label` (1 = FAIL, 0 = PASS/other) and `timestamp`
- Missing values strategy:
  - Numeric cold-start sentinels (`-1`, `999`) are preserved as-is (model handles them)
  - Null values that are not intentional sentinels raise `ValueError` during build
- Processing is commit-batched: all tests for a given commit share the same commit-level features (computed once)
- Progress logged to stdout: `"Processing commit {i}/{n}: {sha[:8]}"` every 10 commits
- Output saved to `data/features/{repo_name}_features.parquet`

---

### S2-06 · End-to-end data_pipeline.py

**Priority:** Critical  
**Estimate:** 5h

**Description:**  
Create the single-command entry point that runs the full feature extraction pipeline for a given RTPTorrent project.

**Acceptance Criteria:**
- Script at `scripts/data_pipeline.py`
- CLI: `python scripts/data_pipeline.py --project <user>@<project> --db-path PATH --rtp-path PATH --output-path PATH`
- Execution sequence: load test_runs + file_changes from DB → instantiate extractors → run FeatureJoiner → save Parquet
- Completes in ≤ 5 minutes for a single project on standard laptop hardware
- Prints final summary: `"Done. Shape: (N rows, M cols). Label distribution: {0: X, 1: Y}. commit_meta_missing: Z rows."`
- Idempotent: if output Parquet already exists, prints `"Output exists. Use --force to overwrite."` and exits 0

---

### S2-07 · Missing value strategy & data integrity checks

**Priority:** High  
**Estimate:** 4h

**Description:**  
Add a validation step that runs after `FeatureJoiner` to catch data quality issues before the Parquet file is written.

**Acceptance Criteria:**
- Function `validate_features(df: pd.DataFrame) -> None` in `src/features/validation.py`
- Raises `AssertionError` with a descriptive message if any of the following fail:
  - `df.shape[0] > 0`
  - No column has `null` count > 5% of rows (except intentional sentinel columns)
  - `label` column contains only values in `{0, 1}`
  - `timestamp` column is monotonically non-decreasing within each `test_id` group (verifies ordering)
  - Feature count ≥ 20
- Called automatically at the end of `data_pipeline.py`

---

### S2-08 · EDA notebook

**Priority:** High  
**Estimate:** 6h

**Description:**  
Produce a fully executed EDA notebook that characterises the feature matrix and identifies the most predictive features before model training begins.

**Acceptance Criteria:**
- Notebook at `notebooks/02_eda_features.ipynb`
- All cells executed top-to-bottom without errors against `full_features.parquet`
- Must contain:
  1. Dataset summary: shape, label distribution, per-repo breakdown
  2. Missing value heatmap (seaborn)
  3. Correlation matrix of all numeric features vs `label` (top 15 by absolute correlation)
  4. Mutual information score ranking of all features vs `label`
  5. Distribution plots for top-5 features by MI score (histogram + KDE)
  6. `days_since_last_fail` vs `failure_rate_30d` scatter plot coloured by `label`
- Written conclusion cell (markdown): "Top 3 most predictive features and why"

---

### S2-09 · Unit test suite completion

**Priority:** High  
**Estimate:** 6h

**Description:**  
Ensure full unit test coverage for all extractor classes before the feature pipeline is declared production-ready.

**Acceptance Criteria:**
- `pytest tests/` exits 0 with 0 failures
- Test files:
  - `tests/test_commit_extractor.py` — ≥ 8 test cases
  - `tests/test_test_history_extractor.py` — ≥ 10 test cases (including cold start, boundary conditions)
  - `tests/test_dependency_extractor.py` — ≥ 6 test cases (including parse failure)
  - `tests/test_feature_joiner.py` — ≥ 4 integration-style tests with a small synthetic DB
- No test uses the real cloned repos (all tests use fixtures or small synthetic data)
- `pytest --tb=short -q` output recorded in `docs/test-results-sprint2.txt`

---

## Sprint 2 — Dependency Map

```
S2-01 (commit features) ──┐
S2-02 (author history)  ──┤
S2-03 (test history)    ──┼──→ S2-05 (FeatureJoiner) ──→ S2-06 (pipeline) ──→ S2-07 (validation)
S2-04 (dependency)      ──┘                                                  ↓
                                                                         S2-08 (EDA)
S2-09 (unit tests) ← depends on all extractor stories being complete
```

---

## Milestone M1 Checklist (end of Sprint 2)

- [ ] `python scripts/data_pipeline.py --project apache@sling --db-path data/test_history.db --rtp-path references/rtp-torrent-v11/rtp-torrent --output-path data/features/apache@sling.parquet` runs without errors
- [ ] Output shape: ≥ (5000, 20)
- [ ] `pytest tests/` → 0 failures
- [ ] `notebooks/02_eda_features.ipynb` executed cleanly
- [ ] **Decision recorded:** top-5 features confirmed; no data leakage found; `commit_meta_missing` rate documented

> After M1: feature pipeline is frozen. No changes to extractor logic from Sprint 3 onward unless a critical bug is found.

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `javalang` fails on some Java syntax | Low | Low | RTPTorrent repos are Java 8/11 era; wrap all parse calls in try/except; log parse failure rate |
| Feature join is too slow (> 30 min) | Medium | Medium | Cache commit-level features by SHA; process test-level in vectorised pandas operations; patches.csv file-list avoids per-commit git diff |
| High `commit_meta_missing` rate (> 30%) | Medium | Medium | Fall back to patches.csv for file features; zero out line-count features; note as limitation |
| `file_changes` table has commits not present in cloned repo (fork commits) | Medium | Low | Graceful skip on git lookup; file-list features still available from patches.csv |
| High correlation between feature groups (multicollinearity) | Low | Low | Document in EDA; XGBoost handles this natively; not a blocker |
