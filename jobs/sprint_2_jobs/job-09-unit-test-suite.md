---
# Job 09: Unit Test Suite Completion

## Objective
Ensure all extractor classes from jobs 01–05 have complete unit test coverage meeting the minimum case counts specified in the backlog. `pytest tests/` must exit 0 with 0 failures. Record the `pytest --tb=short -q` output to `docs/test-results-sprint2.txt`.

## Sprint Goal Alignment
This job is the final quality gate before the feature pipeline is declared production-ready. The sprint Definition of Done requires `pytest tests/` to pass 100% — this job verifies and fills any gaps left by individual extractor jobs.

## Dependencies
- Upstream: all extractor jobs (01–05) must be complete; their respective test files may already exist with partial coverage
- Downstream: Sprint 3 (model training) requires a green test suite before feature pipeline is frozen; post-M1 freeze means no extractor changes from Sprint 3 onward

## Scope (in)
Audit and complete the following test files to meet minimum case counts:

| Test file | Minimum cases | Coverage target |
|---|---|---|
| `tests/test_commit_extractor.py` | ≥ 8 | job-01 + job-02 cases combined |
| `tests/test_test_history_extractor.py` | ≥ 10 | including cold start, boundary conditions |
| `tests/test_dependency_extractor.py` | ≥ 6 | including parse failure |
| `tests/test_feature_joiner.py` | ≥ 4 | integration-style with synthetic DuckDB |

- All test files must pass `pytest` with 0 failures
- No test accesses real cloned repos (`data/git-repos/`) or the real `data/test_history.db`
- All git interactions mocked via `unittest.mock` or `pytest-mock`
- All DuckDB interactions in FeatureJoiner tests use in-memory DuckDB (`duckdb.connect(':memory:')`)
- Run output recorded: `pytest --tb=short -q > docs/test-results-sprint2.txt`

**Required test cases by file (gaps to fill if not already covered by individual jobs):**

`tests/test_commit_extractor.py` (≥ 8 total, jobs 01 + 02):
1. Normal commit — all 11 features returned, correct values
2. Merge commit — `is_merge_commit=1`, diff against first parent
3. Initial commit (no parents) — diff features zeroed
4. Commit not found in repo — `commit_meta_missing=1`, metadata features zeroed
5. Commit with no Java files — `java_files_changed=0`, others may be non-zero
6. Keyword matching — commit message with "hotfix" and "error" → `keyword_risk_score=2`
7. `test/` path detection — file under `src/test/java/` counted in `test_files_changed`, not `source_files_changed`
8. Author features: timestamp path — future commits excluded from 90d window
9. Author features: fallback path — all timestamps NULL → `author_feature_fallback=1`, `feature_source='job_sequence'`
10. Unseen author (< 3 commits in window) → `author_failure_rate_90d=-1`

`tests/test_test_history_extractor.py` (≥ 10 total):
1. Cold start — no prior history → all sentinel values
2. Only failures — `last_outcome=1`, `consecutive_passes=0`
3. Only passes — `last_outcome=0`, `consecutive_passes=N`
4. Mixed history — verify `failure_rate_30d` computation
5. Time boundary exactness — record at exactly `as_of_ts` NOT included
6. 90d window boundary — record at `as_of_ts - 90*86400 - 1` NOT included; record at `as_of_ts - 90*86400` IS included
7. `duration_variance=0` when < 2 records in last 20 runs
8. `days_since_last_fail=999` when test has never failed
9. `run_count_30d` correct count
10. NULL timestamp rows handled via pseudo-timestamp fallback

`tests/test_dependency_extractor.py` (≥ 6 total):
1. Test file not on disk → all zeros + `dependency_parse_failed=1`
2. `javalang` parse failure (malformed Java) → all zeros + `dependency_parse_failed=1`, no exception
3. `test_file_touched=1` when test file appears in `changed_java_files`
4. `import_overlap` — 2 changed files whose class names appear in imports → `import_overlap=2`
5. `same_package=1` when changed source shares package
6. `changed_files_in_module` — count files sharing same Maven module root

`tests/test_feature_joiner.py` (≥ 4 total):
1. Output shape: 3 commits × 2 tests = 6 rows, ≥ 20 feature columns
2. All expected columns present (including `feature_source`, `label`, `timestamp`, `commit_sha`, `test_id`)
3. Commit-level features are identical for all rows sharing the same `commit_sha`
4. Non-sentinel NULL raises `ValueError`

## Out of Scope
- `validate_features()` unit tests — these are integration-tested via `data_pipeline.py` running against real Parquet; no separate unit test file is required for job-07
- End-to-end pipeline tests against real data — those are verification commands for job-06
- Coverage % measurement — minimum case counts are the acceptance criterion, not a coverage percentage target

## Implementation Notes
**Synthetic DuckDB for FeatureJoiner tests:**
```python
import duckdb, pandas as pd

con = duckdb.connect(':memory:')
con.execute("""
  CREATE TABLE test_runs (
    repo VARCHAR, commit_sha VARCHAR, test_id VARCHAR,
    outcome VARCHAR, timestamp BIGINT, job_sequence BIGINT,
    job_id BIGINT, duration_ms FLOAT, author_email VARCHAR
  )
""")
con.execute("""
  CREATE TABLE file_changes (
    repo VARCHAR, commit_sha VARCHAR, filepath VARCHAR
  )
""")
# Insert 3 commits × 2 tests = 6 rows
```

**Mocking git.Repo:** use `unittest.mock.MagicMock()` for `git.Repo`; set `.commit(sha)` return value to a mock commit object with `.parents`, `.diff()`, `.message`, `.author.email`, `authored_datetime` attributes.

**Fixture `.java` file for dependency tests:** write a small synthetic Java source string directly in the test (no file I/O):
```python
JAVA_SOURCE = """
package com.example;
import com.other.Foo;
import com.another.Bar;
public class FooTest { }
"""
```
Mock `open()` or `pathlib.Path.read_text()` to return this string.

**Test isolation:** each test must be independent — no shared state between test functions. Use `pytest` fixtures for setup.

## Deliverables
- Completed (or verified complete) test files:
  - `tests/test_commit_extractor.py`
  - `tests/test_test_history_extractor.py`
  - `tests/test_dependency_extractor.py`
  - `tests/test_feature_joiner.py`
- `docs/test-results-sprint2.txt` — recorded `pytest --tb=short -q` output

## Verification
```bash
pytest tests/ --tb=short -q
# Expected: X passed, 0 failed in <Ys>

pytest tests/ --tb=short -q > docs/test-results-sprint2.txt && cat docs/test-results-sprint2.txt
```

## Definition of Done
- [ ] `pytest tests/` exits 0 with 0 failures
- [ ] `tests/test_commit_extractor.py` has ≥ 8 test cases (jobs 01 + 02 combined)
- [ ] `tests/test_test_history_extractor.py` has ≥ 10 test cases including cold start and boundary exactness
- [ ] `tests/test_dependency_extractor.py` has ≥ 6 test cases including parse failure
- [ ] `tests/test_feature_joiner.py` has ≥ 4 integration-style tests with synthetic in-memory DuckDB
- [ ] No test accesses real repos or `data/test_history.db`
- [ ] `docs/test-results-sprint2.txt` recorded with full `pytest --tb=short -q` output
---
