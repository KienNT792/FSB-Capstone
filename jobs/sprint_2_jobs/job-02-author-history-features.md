---
# Job 02: CommitFeatureExtractor — Author History Features

## Objective
Extend `CommitFeatureExtractor` (created in job-01) with method `extract_author_features(commit_sha: str, history_df: pd.DataFrame) -> dict` that returns 2 time-aware per-author features plus 2 audit flags (`author_feature_fallback`, `feature_source`). The method must implement two distinct execution paths — timestamp-based (primary) and job_sequence-based (fallback) — and correctly gate on which path applies per row. The `feature_source` column it produces is the audit column validated in job-07.

## Sprint Goal Alignment
This job produces `author_commit_count_90d` and `author_failure_rate_90d` columns, which are part of the ≥ 20 feature requirement in the sprint Definition of Done. It also produces the `feature_source` audit column that job-07 (validation) checks against the null `commit_sha` baseline per project.

## Dependencies
- Upstream:
  - job-00: per-project decision table must be in `docs/decisions-log.md`; `timestamp` populated for TIMESTAMP_OK projects (primary path requires non-NULL timestamps in `history_df`)
  - job-01: `CommitFeatureExtractor` class must exist (this job adds a method to it)
- Downstream: job-05 (FeatureJoiner calls `extract_author_features()` per `(commit, test)` pair, passing the pre-loaded `history_df`), job-09 (unit tests)

## Scope (in)
- Method `extract_author_features(commit_sha: str, history_df: pd.DataFrame) -> dict` added to `CommitFeatureExtractor`
- `history_df` columns: `[commit_sha, outcome, timestamp, job_sequence, author_email]`
- Returns:

| Feature | Type | Description |
|---|---|---|
| `author_commit_count_90d` | int | Commits by this author in past 90 days |
| `author_failure_rate_90d` | float | Fraction of author's commits with ≥ 1 FAIL, past 90 days |
| `author_feature_fallback` | int | 1 if job_sequence path was used, 0 if timestamp path |
| `feature_source` | str | `'timestamp'` or `'job_sequence'` |

- **Primary path (timestamp available):** filter `history_df` to rows where `timestamp < current_commit_timestamp` AND `timestamp >= current_commit_timestamp - 90*86400`. Compute `author_commit_count_90d` and `author_failure_rate_90d` over this filtered set. Set `feature_source='timestamp'`, `author_feature_fallback=0`.
- **Fallback path trigger:** use job_sequence path if `current_commit_timestamp IS NULL` OR `(count of NULL timestamps in history_df) / len(history_df) > 0.10`. In fallback: filter to rows where `job_sequence < current_job_sequence`. No 90-day window — use all prior jobs. `author_commit_count_90d` is count of prior jobs by same author; `author_failure_rate_90d` computed over all prior jobs. Set `feature_source='job_sequence'`, `author_feature_fallback=1`.
- Authors with < 3 commits in window (either path): return `author_failure_rate_90d = -1` (unseen flag). `author_commit_count_90d` still reflects actual count.
- Unit tests in `tests/test_commit_extractor.py` covering: timestamp-path filtering (future commits excluded), fallback-path activation when all timestamps NULL, `author_feature_fallback` flag correctness, `feature_source` values constrained to `{'timestamp', 'job_sequence'}`, unseen author (< 3 commits) returns `-1` rate.

## Out of Scope
- Code churn features (`lines_added`, `keyword_risk_score`, etc.) — job-01
- Writing `feature_source` to Parquet — job-05 (FeatureJoiner assembles the final DataFrame including this column)
- Per-project tolerance validation of `feature_source` ratio — job-07
- Any modification to `test_runs` or `file_changes` tables

## Implementation Notes
**Per-project tolerance table** (for reference — enforcement is in job-07, not here):

| Project | Null `commit_sha` % (baseline) | Tolerance type | Tolerance |
|---|---:|---|---|
| `adamfisk@LittleProxy` | 30.42% | relative | ±1% |
| `l0rdn1kk0n@wicket-bootstrap` | 19.33% | relative | ±1% |
| `thinkaurelius@titan` | 12.91% | relative | ±1% |
| `deeplearning4j@deeplearning4j` | 5.70% | relative | ±1% |
| `neuland@jade4j` | 0.10% | absolute | ±0.5 percentage points |

**Fallback threshold:** the `> 10%` NULL timestamp fraction check is a project-level signal. In practice, LittleProxy has 30.42% null-SHA rows (which are also null-timestamp rows); these rows will trigger the fallback path individually since their own `timestamp` is NULL.

**`author_email` resolution:** the `history_df` passed in by FeatureJoiner must include `author_email`. This field is NOT in `test_runs` — it must be resolved from the git commit object by FeatureJoiner before calling this method. Document this pre-condition in the method docstring.

**Leakage guard:** the `timestamp < current_commit_timestamp` filter (strict less-than, not less-than-or-equal) prevents same-commit test outcomes from contaminating the author's history. Verify this in the time-boundary unit test.

**`feature_source` is an audit column only** (Decision 5 in `docs/decisions-log.md`): it is returned in the dict so FeatureJoiner can write it to the Parquet, but it must NOT be in the `X` matrix passed to model training. FeatureJoiner is responsible for excluding it; this method just returns it.

## Deliverables
- `src/features/commit_extractor.py` — `extract_author_features()` method added
- `tests/test_commit_extractor.py` — author-history test cases added (total file must reach ≥ 8 test cases when combined with job-01 cases)

## Verification
```bash
pytest tests/test_commit_extractor.py -v -k "author"
```
All author-related cases pass. Timestamp-path and fallback-path are exercised by separate test cases.

## Definition of Done
- [ ] `extract_author_features()` method exists on `CommitFeatureExtractor`
- [ ] Primary timestamp path: only commits with `timestamp < current_commit_timestamp` included
- [ ] 90-day window applied correctly in timestamp path (86400s × 90)
- [ ] Fallback path activates when `current_commit_timestamp IS NULL` or > 10% NULL timestamps in `history_df`
- [ ] Fallback path: no time-box, uses `job_sequence < current_job_sequence`
- [ ] Authors with < 3 commits return `author_failure_rate_90d = -1`
- [ ] `feature_source` values constrained to `{'timestamp', 'job_sequence'}` only
- [ ] `author_feature_fallback` flag is 0 (timestamp path) or 1 (fallback path) only
- [ ] All unit tests pass; no test accesses real cloned repos
---
