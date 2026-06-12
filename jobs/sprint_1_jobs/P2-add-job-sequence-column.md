# P2 — Add `job_sequence` Column to DuckDB Schema

**Priority:** P2  
**Effort estimate:** 1–2 hours  
**Blocking:** Hard blocker for S2-01 (TimeSeriesSplit temporal ordering)  
**Status:** DONE (verified 2026-06-10 — column existed and fully populated prior to job execution; load_rtp_dataset.py DDL and populate_job_sequence() were already correct)

---

## Context

`decisions-log.md` (2026-05-20): *"Temporal splitting must fall back to per-project `job_sequence` until timestamp enrichment is done."*

`sprint-1-backlog.md` S1-06 specifies `job_sequence INTEGER` as a required column in `test_runs`, populated via `DENSE_RANK() OVER (PARTITION BY repo ORDER BY CAST(job_id AS INTEGER))`. The column is currently **absent** from the schema.

Sprint 2's `TimeSeriesSplit` (S2-01) reads `job_sequence` as the ordering fallback when `timestamp IS NULL`. Without this column, S2-01 will fail at import or produce unordered splits, causing data leakage.

Current schema columns (confirmed):
```
id, repo, job_id, commit_sha, test_id, test_index, outcome, duration_ms, timestamp, run_count
```

Missing: `job_sequence`

---

## Tasks

### 1. Add column to existing DB

Run this SQL against `data/test_history.db`:

```sql
ALTER TABLE test_runs ADD COLUMN job_sequence INTEGER;
```

### 2. Populate column with DENSE_RANK equivalent

DuckDB supports `UPDATE ... FROM (subquery with window function)` natively. Run once per selected project:

```sql
UPDATE test_runs
SET job_sequence = ranked.seq
FROM (
    SELECT job_id,
           DENSE_RANK() OVER (ORDER BY TRY_CAST(job_id AS BIGINT) NULLS LAST, job_id) AS seq
    FROM test_runs
    WHERE repo = '<project>'
) AS ranked
WHERE test_runs.repo = '<project>'
  AND test_runs.job_id = ranked.job_id;
```

Or via Python to iterate all distinct repos:

```python
import duckdb

con = duckdb.connect("data/test_history.db")

repos = [row[0] for row in con.execute("SELECT DISTINCT repo FROM test_runs").fetchall()]
for repo in repos:
    con.execute("""
        UPDATE test_runs
        SET job_sequence = ranked.seq
        FROM (
            SELECT job_id,
                   DENSE_RANK() OVER (ORDER BY TRY_CAST(job_id AS BIGINT) NULLS LAST, job_id) AS seq
            FROM test_runs
            WHERE repo = ?
        ) AS ranked
        WHERE test_runs.repo = ?
          AND test_runs.job_id = ranked.job_id;
    """, (repo, repo))
    con.commit()
    print(f"Updated job_sequence for {repo}")

con.close()
```

### 3. Verify the update

```python
import duckdb
con = duckdb.connect("data/test_history.db")

# Check column exists
cols = [r[0] for r in con.execute("DESCRIBE test_runs").fetchall()]
assert "job_sequence" in cols, "Column missing!"

# Check no NULLs remain
null_count = con.execute("SELECT COUNT(*) FROM test_runs WHERE job_sequence IS NULL").fetchone()[0]
print(f"NULL job_sequence rows: {null_count}")  # should be 0

# Spot-check: per-repo sequence range
rows = con.execute("""
    SELECT repo, MIN(job_sequence), MAX(job_sequence), COUNT(DISTINCT job_sequence)
    FROM test_runs
    GROUP BY repo
    ORDER BY repo
""").fetchall()
for r in rows:
    print(r)

con.close()
```

### 4. Update `data/scripts/load_rtp_dataset.py`

Add `job_sequence` to the `CREATE TABLE` DDL so future fresh loads include it:

```sql
job_sequence INTEGER,   -- DENSE_RANK on CAST(job_id AS INTEGER) within each repo
```

After bulk insert of a project's rows, add a post-load step that computes and sets `job_sequence` for the newly inserted repo. Reference the implementation notes in `sprint-1-backlog.md` S1-06.

Also add `CREATE INDEX IF NOT EXISTS idx_test_runs_job_seq ON test_runs(repo, job_sequence);` to the schema.

---

## Verification

```powershell
python -c "
import duckdb
c = duckdb.connect('data/test_history.db')
cols = [r[0] for r in c.execute('DESCRIBE test_runs').fetchall()]
print('Columns:', cols)
print('NULL job_sequence:', c.execute('SELECT COUNT(*) FROM test_runs WHERE job_sequence IS NULL').fetchone()[0])
r = c.execute('SELECT repo, MIN(job_sequence), MAX(job_sequence) FROM test_runs GROUP BY repo LIMIT 5').fetchall()
for row in r: print(row)
c.close()
"
```

---

## Done Criteria

- `job_sequence` column exists in `test_runs`
- Zero NULL values in `job_sequence`
- `load_rtp_dataset.py` DDL and post-load logic updated to include `job_sequence`
- Verification script prints expected per-repo range without errors
