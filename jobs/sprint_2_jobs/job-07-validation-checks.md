---
# Job 07: Missing Value Strategy & Data Integrity Checks

## Objective
Implement `validate_features(df: pd.DataFrame) -> None` in `src/features/validation.py`. The function raises `AssertionError` with a descriptive message if any of 7 integrity checks fail. It is called automatically by `data_pipeline.py` (job-06) after `FeatureJoiner.build()` returns, before the Parquet is written.

## Sprint Goal Alignment
This job is the quality gate that enforces the sprint's "no data leakage, ≥ 20 features" requirement. It catches join bugs (via `feature_source` ratio check), time-ordering violations (via monotonicity check), and schema drift (via column count and NULL checks) before bad data reaches Sprint 3 model training.

## Dependencies
- Upstream:
  - job-05: `validate_features()` receives the DataFrame returned by `FeatureJoiner.build()` — the column set must match what job-05 produces
  - job-02: `feature_source` column (values `'timestamp'` | `'job_sequence'`) must be present
  - job-00: per-project null `commit_sha` baseline fractions (used in check 6) are fixed constants from `data/rtp-project-summary.md`
- Downstream: job-06 (calls `validate_features()` in the pipeline sequence)

## Scope (in)
- Function `validate_features(df: pd.DataFrame) -> None` in `src/features/validation.py`
- All 7 checks must be implemented; each raises `AssertionError` with a message that names the failing check and shows the actual value:

**Check 1 — Non-empty:**
```python
assert df.shape[0] > 0, f"DataFrame is empty (0 rows)"
```

**Check 2 — NULL rate:**
```python
# Exempt columns: timestamp, feature_source, and intentional sentinel columns
# Intentional sentinels (value -1 or 999 is expected, but NULL is not):
#   failure_rate_7d, failure_rate_30d, failure_rate_90d, last_outcome,
#   author_failure_rate_90d, days_since_last_fail, days_since_last_run
exempt = {'timestamp', 'feature_source', 'commit_sha', 'test_id'}
for col in df.columns:
    if col in exempt:
        continue
    null_pct = df[col].isnull().mean()
    assert null_pct <= 0.05, f"Column '{col}' has {null_pct:.1%} NULL (threshold: 5%)"
```

**Check 3 — Label values:**
```python
assert set(df['label'].unique()).issubset({0, 1}), \
    f"label column contains unexpected values: {set(df['label'].unique()) - {0, 1}}"
```

**Check 4 — Timestamp monotonicity per test_id:**
```python
# Only for rows where timestamp IS NOT NULL
ts_df = df[df['timestamp'].notna()].sort_values(['test_id', 'timestamp'])
assert (ts_df.groupby('test_id')['timestamp'].is_monotonic_increasing).all(), \
    "timestamp is not monotonically non-decreasing within at least one test_id group"
```

**Check 5 — feature_source values:**
```python
valid_fs = {'timestamp', 'job_sequence'}
actual_fs = set(df['feature_source'].unique())
assert actual_fs.issubset(valid_fs), \
    f"feature_source contains unexpected values: {actual_fs - valid_fs}"
```

**Check 6 — feature_source ratio per project (per-project tolerance table):**

Per-project baselines and tolerances (hardcoded constants — these are fixed from Sprint 1 data):

| Project | Null `commit_sha` % baseline | Tolerance type | Tolerance |
|---|---:|---|---|
| `adamfisk@LittleProxy` | 30.42 | relative | 1.0% |
| `l0rdn1kk0n@wicket-bootstrap` | 19.33 | relative | 1.0% |
| `thinkaurelius@titan` | 12.91 | relative | 1.0% |
| `deeplearning4j@deeplearning4j` | 5.70 | relative | 1.0% |
| `neuland@jade4j` | 0.10 | absolute | 0.5 pp |

For each project present in `df` (identified by `repo` column — verify column name in FeatureJoiner output):
```python
observed_pct = (df[df['repo'] == project]['feature_source'] == 'job_sequence').mean() * 100
if tolerance_type == 'relative':
    assert abs(observed_pct - baseline) <= baseline * 0.01, \
        f"{project}: feature_source job_sequence ratio {observed_pct:.2f}% vs baseline {baseline:.2f}% (relative ±1%)"
else:  # absolute
    assert abs(observed_pct - baseline) <= 0.5, \
        f"{project}: feature_source job_sequence ratio {observed_pct:.2f}% vs baseline {baseline:.2f}% (absolute ±0.5pp)"
```

**Check 7 — Feature count ≥ 20:**
```python
excluded = {'commit_sha', 'test_id', 'label', 'timestamp', 'feature_source'}
feature_cols = [c for c in df.columns if c not in excluded]
assert len(feature_cols) >= 20, \
    f"Only {len(feature_cols)} feature columns (need ≥ 20, excluded: {excluded})"
```

## Out of Scope
- Fixing bad data — this function only detects and reports; it does not mutate the DataFrame
- Calling `validate_features()` — job-06 is responsible for calling it
- Any write to DuckDB or Parquet

## Implementation Notes
**`repo` column in DataFrame:** verify that FeatureJoiner includes a `repo` column in the output (needed for Check 6 per-project grouping). If not present, FeatureJoiner must be updated to include it. Coordinate with job-05.

**Check 4 edge case:** if a `test_id` has only one row with a non-NULL timestamp, `is_monotonic_increasing` returns True (trivially). This is correct behaviour.

**Check 6 note on rolling-window leading-row drops:** rolling-window features (`failure_rate_7d/30d/90d`) drop leading rows per project, and this drop is not evenly distributed between the timestamp and job_sequence ordering paths. This is why the tolerance is ±1% relative (not exact match) and why jade4j uses absolute tolerance. Do not try to compensate for this in validation logic — the tolerance table already accounts for it.

**`feature_source` column is audit-only** (Decision 5 in `docs/decisions-log.md`): Check 7 explicitly excludes it from the ≥ 20 feature count, consistent with the decision that `feature_source` is not a model input.

## Deliverables
- `src/features/validation.py`
- Unit tests for `validate_features()` are covered under job-09 (no separate test file required for this job)

## Verification
```bash
# Validation runs automatically at end of data_pipeline.py
# To test directly:
python -c "
import pandas as pd
from src.features.validation import validate_features
df = pd.read_parquet('data/features/neuland@jade4j_features.parquet')
validate_features(df)
print('All checks passed.')
"
```

## Definition of Done
- [ ] `validate_features()` exists at `src/features/validation.py`
- [ ] All 7 checks implemented with descriptive `AssertionError` messages
- [ ] Per-project tolerance table hardcoded with correct baselines from `data/rtp-project-summary.md`
- [ ] jade4j uses absolute ±0.5 pp tolerance; all others use relative ±1%
- [ ] `feature_source` excluded from Check 7 feature count
- [ ] `timestamp` and `feature_source` exempted from Check 2 NULL rate
- [ ] Called automatically by `data_pipeline.py` after `FeatureJoiner.build()` returns
---
