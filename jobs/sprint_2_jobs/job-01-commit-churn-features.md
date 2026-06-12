---
# Job 01: CommitFeatureExtractor — Code Churn Features

## Objective
Implement `CommitFeatureExtractor` at `src/features/commit_extractor.py` with method `extract(commit_sha: str) -> dict` that returns 11 commit-level features (4 file-list features from DuckDB `file_changes` table + 7 metadata features from gitpython diff). The class must handle four edge cases without raising: merge commit, initial commit (no parents), commit not found in cloned repo, commit with no Java files.

## Sprint Goal Alignment
This job produces commit-level columns (`files_changed_total`, `java_files_changed`, `lines_added`, `keyword_risk_score`, etc.) that job-05 (FeatureJoiner) consumes as the "commit block" shared across all tests for a given SHA. Computing them once per commit and broadcasting to all `(commit, test)` pairs is the primary performance lever for keeping pipeline runtime ≤ 5 minutes.

## Dependencies
- Upstream:
  - job-00: requires `timestamp` populated in `test_runs` and per-project decision table in `docs/decisions-log.md` (gate must be passed before this job starts)
  - `data/test_history.db` populated with `file_changes` table (Sprint 1 deliverable)
  - Git repos cloned under `data/git-repos/<owner>@<repo>` (Sprint 1 deliverable)
- Downstream: job-05 (FeatureJoiner calls `CommitFeatureExtractor.extract()` per unique commit SHA), job-09 (unit tests)

## Scope (in)
- Class `CommitFeatureExtractor` with constructor `__init__(self, repo: git.Repo, db_path: str)`
- Method `extract(commit_sha: str) -> dict` returning all 11 features below
- File-list features sourced from `file_changes` table (fast path — no git subprocess):

| Feature | Type | Description |
|---|---|---|
| `files_changed_total` | int | Total files in `file_changes` for this SHA |
| `java_files_changed` | int | `.java` files only |
| `source_files_changed` | int | `.java` files not under `test/` path |
| `test_files_changed` | int | `.java` files under `test/` path |

- Commit metadata features sourced from gitpython diff (requires cloned repo):

| Feature | Type | Description |
|---|---|---|
| `lines_added` | int | Total `+` lines across all changed files |
| `lines_deleted` | int | Total `-` lines across all changed files |
| `churn_total` | int | `lines_added + lines_deleted` |
| `is_merge_commit` | int | 1 if commit has > 1 parent, else 0 |
| `commit_hour` | int | Hour of `authored_datetime` (0–23) |
| `commit_day_of_week` | int | Weekday of `authored_datetime` (0=Mon) |
| `keyword_risk_score` | int | Count of risk keywords in commit message |

- Risk keywords list (exact): `["fix", "hotfix", "bug", "patch", "revert", "urgent", "crash", "error", "broken", "regression"]`
- Fallback when `commit_sha` not found in repo: return zeros for all metadata features + `commit_meta_missing=1`
- Fallback for initial commit (no parents): return zeros for diff-based features (`lines_added`, `lines_deleted`, `churn_total`)
- Unit tests in `tests/test_commit_extractor.py` covering ≥ 8 cases: normal commit, merge commit, initial commit, commit not found (meta missing), commit with no Java files, keyword matching, `test/` path detection, zero churn

## Out of Scope
- Author history features (`author_failure_rate_90d`, `author_commit_count_90d`) — those are job-02's `extract_author_features()` method
- `feature_source` column — written by job-05 (FeatureJoiner), not here
- Test history rolling statistics (`failure_rate_7d`, etc.) — job-03
- Dependency/import overlap features — job-04
- Any write to `data/features/` — job-05

## Implementation Notes
- Constructor connects to DuckDB for `file_changes` queries; use `duckdb.connect(db_path, read_only=True)` to avoid locking conflicts when pipeline runs in parallel.
- `file_changes` table columns: `repo`, `commit_sha`, `filepath` (verify exact schema in `data/test_history.db` before coding).
- `source_files_changed`: `.java` files where `filepath` does NOT contain `/test/` (case-insensitive match sufficient for RTPTorrent repos).
- `test_files_changed`: `.java` files where `filepath` DOES contain `/test/`.
- gitpython diff: `repo.commit(sha).diff(repo.commit(sha).parents[0])` for non-initial commits. Each diff item has `.diff` attribute (bytes) — count `+`/`-` lines by splitting on `\n`.
- keyword matching: case-insensitive substring search of commit message against each keyword in the list; `keyword_risk_score` is total count of keywords found (a commit containing both "fix" and "bug" scores 2).
- `commit_meta_missing=1` must be included as a column in the returned dict even when the commit IS found (value 0 in normal case). job-05 uses this flag to track the `commit_meta_missing` rate in the summary line.

## Deliverables
- `src/features/commit_extractor.py`
- `tests/test_commit_extractor.py` (≥ 8 test cases, no real repo — use `unittest.mock` or `pytest-mock`)

## Verification
```bash
pytest tests/test_commit_extractor.py -v
```
All 8+ cases pass. No `git.Repo` calls hit real disk (mocked).

## Definition of Done
- [ ] `CommitFeatureExtractor` class exists at `src/features/commit_extractor.py`
- [ ] `extract()` returns dict with all 11 features + `commit_meta_missing` key
- [ ] File-list features sourced from `file_changes` DuckDB table (not live git diff)
- [ ] Risk keyword list matches exact 10 terms from backlog
- [ ] All 4 edge cases handled without raising: merge commit, initial commit, commit not found, no Java files
- [ ] `pytest tests/test_commit_extractor.py` passes with ≥ 8 test cases
- [ ] No test accesses real cloned repos
---
