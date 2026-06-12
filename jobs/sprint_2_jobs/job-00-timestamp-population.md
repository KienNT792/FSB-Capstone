---
# Job 00: Timestamp Population — Git Commit Date Resolution

## Objective
Run a per-project SHA-resolution coverage check (timebox: 2h total). For each of the 5 selected projects, determine what fraction of distinct `commit_sha` values in `test_runs` can be resolved to a `committed_date` from the local git clone. Apply the following per-project decision rule and write the outcomes to `docs/decisions-log.md`:

- **Coverage ≥ 70%:** run `scripts/add_timestamps.py` for that project; mark status `TIMESTAMP_OK`.
- **Coverage < 70%:** do NOT run `add_timestamps.py` for that project; mark status `JOB_SEQUENCE_FALLBACK`; record a caveat entry in `docs/decisions-log.md` in the same style as the existing LittleProxy/titan low-failure-rate caveats.

job-01 and job-02 MAY proceed for ALL 5 projects once the per-project decision table is written to `docs/decisions-log.md` — do NOT block them globally on a single project's coverage failure.

> Note: Sprint 1 already achieved 100% SHA coverage for all 5 projects (see `data/rtp-project-summary.md` Timestamp Population Status). This job is therefore a verification/gate step — re-run the check, confirm TIMESTAMP_OK for all 5, and record the table. No fallback entries are expected.

## Sprint Goal Alignment
This job produces the `timestamp` column in `test_runs` (DuckDB) and the per-project decision table in `docs/decisions-log.md`. job-01 and job-02 consume `timestamp` directly for time-aware feature computation; without it, all author history features degenerate to `job_sequence` fallback ordering.

## Dependencies
- Upstream: Sprint 1 S1-03 (repos cloned under `data/git-repos/<owner>@<repo>`); `data/test_history.db` loaded and non-empty.
- Downstream: job-01, job-02 (both require the per-project decision table to be written before starting)

## Scope (in)
- Run SHA-resolution coverage check: for each project, count distinct `commit_sha` values in `test_runs` where `commit_sha IS NOT NULL` and attempt git lookup.
- Execute `scripts/add_timestamps.py` for projects with coverage ≥ 70% (expected: all 5).
- Write per-project decision table to `docs/decisions-log.md` with columns: project, resolved SHAs, eligible rows, coverage %, status (TIMESTAMP_OK | JOB_SEQUENCE_FALLBACK).
- Print unresolved count per project after run.
- `job_sequence` column remains populated and valid as fallback for any rows where `timestamp` stays NULL after this step.
- Unit test `tests/test_add_timestamps.py`: mock a `git.Repo` with 3 commits; verify correct `UPDATE` calls and NULL-skip behaviour.

## Out of Scope
- Author history feature computation (job-02).
- Temporal split logic (Sprint 3, job-level).
- Modifying the DuckDB schema — `timestamp` column already exists.
- Backfilling rows where `commit_sha IS NULL` — those rows cannot be timestamped by design.

## Implementation Notes
Script: `scripts/add_timestamps.py`

Lookup strategy (already implemented in Sprint 1 — verify still works):
1. `git log --all --format=%H %ct` once per repository — captures reachable commits.
2. `git show --no-patch --format=%H %ct` for unresolved SHAs (orphaned/unreachable objects, e.g. archived repos like jade4j).
3. Batch fallback `git show` calls in chunks of 200 SHAs (Windows command-line length limit).

Expected per-project outcomes (from Sprint 1 run):

| Project | Resolved SHAs | Eligible Rows | Timestamp Row Coverage | Expected Status |
|---|---:|---:|---:|---|
| `adamfisk@LittleProxy` | 262 / 262 | 10,974 | 69.58% | TIMESTAMP_OK |
| `deeplearning4j@deeplearning4j` | 871 / 871 | 14,625 | 94.30% | TIMESTAMP_OK |
| `l0rdn1kk0n@wicket-bootstrap` | 823 / 823 | 38,905 | 80.67% | TIMESTAMP_OK |
| `neuland@jade4j` | 314 / 314 | 35,851 | 99.90% | TIMESTAMP_OK |
| `thinkaurelius@titan` | 382 / 382 | 39,243 | 87.09% | TIMESTAMP_OK |

Note: LittleProxy row coverage is 69.58% — just below 70% — because 30.42% of its rows have `commit_sha IS NULL` and therefore cannot be timestamped by any method. SHA coverage is 100%. Document this distinction explicitly in `docs/decisions-log.md`: the gate is SHA coverage, not row coverage.

## Deliverables
- `scripts/add_timestamps.py` — verified working (or fixed if needed)
- `docs/decisions-log.md` — per-project decision table appended
- `tests/test_add_timestamps.py` — unit test with mocked `git.Repo`
- `data/test_history.db` — `timestamp` column populated for all resolvable rows

## Verification
```bash
# Check timestamp coverage in DuckDB
python -c "
import duckdb
con = duckdb.connect('data/test_history.db')
print(con.execute('''
  SELECT repo,
         COUNT(*) AS total_rows,
         SUM(CASE WHEN timestamp IS NOT NULL THEN 1 ELSE 0 END) AS timestamped,
         ROUND(100.0 * SUM(CASE WHEN timestamp IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct
  FROM test_runs
  GROUP BY repo
  ORDER BY repo
''').df().to_string(index=False))
"

# Run unit tests
pytest tests/test_add_timestamps.py -v
```

Expected output: all 5 projects show ≥ 70% row coverage (LittleProxy ~69.58% is acceptable given 30.42% structurally-null SHA rows — verify SHA coverage is 100%).

## Definition of Done
- [ ] `scripts/add_timestamps.py` runs without errors against all 5 projects
- [ ] Per-project decision table written to `docs/decisions-log.md` with status for each project
- [ ] SHA coverage ≥ 70% confirmed for all 5 projects (or JOB_SEQUENCE_FALLBACK documented for any below 70%)
- [ ] LittleProxy distinction documented: 30.42% null `commit_sha` rows are structurally untimestamp-able; SHA coverage is 100%
- [ ] `job_sequence` column non-NULL for all rows (fallback ordering remains valid)
- [ ] `pytest tests/test_add_timestamps.py` passes
---
