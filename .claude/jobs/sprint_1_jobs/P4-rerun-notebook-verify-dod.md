# P4 — Re-run Validation Notebook and Verify Sprint 1 DoD

**Priority:** P4 (after P1, P2, P3)  
**Effort estimate:** 30 min  
**Blocking:** Sprint 1 Definition of Done proof  
**Status:** DONE (verified 2026-06-10 — all 5 projects [OK], 0 error cells, job_sequence cell passes)

---

## Context

`notebooks/01_ground_truth_validation.ipynb` currently has two failing assertions in the final summary cell (cell-19):

```
adamfisk@LittleProxy: failure_rate=1.19%, null_sha=30.4% [FAIL (failure_rate < 2%)]
thinkaurelius@titan:  failure_rate=1.46%, null_sha=12.9% [FAIL (failure_rate < 2%)]
```

These failures are **by design** — the threshold was lowered to ≥1% per ADR (2026-05-10). The assertion check in the notebook still uses `>= 0.02` (2%) as the threshold, which is now wrong.

**Prerequisites:** P1 (docs sync) and P2 (`job_sequence` column) must be complete before this job runs. P3 (substring fix) is independent but recommended.

---

## Tasks

### 1. Update the assertion threshold in the notebook

In cell-19 (the final `Sprint 1 Acceptance Checks` cell), change the failure rate threshold from 2% to 1%:

```python
# Before
fail_ok = fr >= 0.02

# After
fail_ok = fr >= 0.01
```

Also update the flag threshold comment if present.

### 2. Update `SELECTED_PROJECTS` list if needed

Cell-1 defines:
```python
SELECTED_PROJECTS = [
    "deeplearning4j@deeplearning4j",
    "l0rdn1kk0n@wicket-bootstrap",
    "neuland@jade4j",
    "adamfisk@LittleProxy",
    "thinkaurelius@titan",
]
```

This is already correct (5 projects). No change needed here.

### 3. Add a `job_sequence` verification cell

After P2 is complete, add a new cell before cell-19 that verifies `job_sequence` is populated:

```python
# Verify job_sequence column
js_nulls = pd.read_sql("SELECT COUNT(*) as n FROM test_runs WHERE job_sequence IS NULL", con).iloc[0,0]
js_sample = pd.read_sql("""
    SELECT repo, MIN(job_sequence) as min_seq, MAX(job_sequence) as max_seq,
           COUNT(DISTINCT job_sequence) as distinct_seqs
    FROM test_runs WHERE repo IN ({})
    GROUP BY repo
""".format(",".join(["?"]*len(SELECTED_PROJECTS))), con, params=SELECTED_PROJECTS)

print(f"NULL job_sequence rows: {js_nulls}")
assert js_nulls == 0, "FAIL: job_sequence has NULL values"
display(js_sample)
print("PASS: job_sequence populated for all rows")
```

### 4. Re-execute the notebook

From repo root with `.venv` active:

```powershell
.\.venv\Scripts\Activate.ps1
jupyter nbconvert --to notebook --execute --inplace notebooks/01_ground_truth_validation.ipynb
```

Or open in Jupyter UI and `Restart Kernel and Run All Cells`.

### 5. Verify all assertion cells pass

Check that the final cell output contains no `[FAIL ...]` lines. Expected output:

```
=== Sprint 1 Acceptance Checks ===
Total test_runs: 22,539,830 (need >= 10,000)
  deeplearning4j@deeplearning4j: failure_rate=6.01%, null_sha=5.7% [OK]
  l0rdn1kk0n@wicket-bootstrap:  failure_rate=22.52%, null_sha=19.3% [OK]
  neuland@jade4j:                failure_rate=3.69%, null_sha=0.1% [OK]
  adamfisk@LittleProxy:          failure_rate=1.19%, null_sha=30.4% [OK]
  thinkaurelius@titan:           failure_rate=1.46%, null_sha=12.9% [OK]

Validation complete.
```

---

## Verification

```powershell
# Check notebook has no error outputs
python -c "
import json
nb = json.load(open('notebooks/01_ground_truth_validation.ipynb'))
errors = [c for c in nb['cells'] if any(o.get('output_type')=='error' for o in c.get('outputs',[]))]
print(f'Error cells: {len(errors)}')
for e in errors:
    print(e['source'][:80])
"
```

---

## Done Criteria

- All notebook cells execute without errors
- Final assertion cell shows `[OK]` for all 5 selected projects
- `job_sequence` verification cell passes
- Notebook outputs committed (or confirmed re-runnable from clean state)
- Sprint 1 Definition of Done checklist in `sprint-1-backlog.md` can be marked fully complete

---

## Sprint 1 → Sprint 2 Handoff Gate

After this job completes, Sprint 1 is **done**. Sprint 2 can begin with:

1. **S2-00** (timestamp population) — clone the 5 selected repos under `data/git-repos/` and run `--add-timestamps`
2. **Confirm `timestamp` coverage ≥ 70%** per project before starting S2-01 or S2-02
3. If coverage fails on LittleProxy or titan, investigate SHA mapping rate (currently 30.4% null SHA for LittleProxy)
