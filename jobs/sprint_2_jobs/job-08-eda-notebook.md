---
# Job 08: EDA Notebook

## Objective
Produce `notebooks/02_eda_features.ipynb` — a fully executed EDA notebook that characterises `full_features.parquet` and identifies the most predictive features before Sprint 3 model training begins. All cells must run top-to-bottom without errors. The notebook must include a written conclusion cell naming the top 3 most predictive features and why.

## Sprint Goal Alignment
This job is the final sprint deliverable after the pipeline is validated. The "decision recorded" item in the Milestone M1 Checklist requires that top-5 features are confirmed and no data leakage is found — the notebook is the evidence artifact for both claims.

## Dependencies
- Upstream:
  - job-06: `data_pipeline.py` must have been run for all 5 selected projects; Parquet files must exist under `data/features/`
  - job-07: `validate_features()` must have passed (clean Parquet is assumed)
- Downstream: Sprint 3 model training uses top-feature findings from this notebook as feature selection input

## Scope (in)
- Notebook at `notebooks/02_eda_features.ipynb`
- All cells executed against the actual Parquet files (not synthetic data)
- Required sections (in order):

  **1. Dataset summary:**
  - Shape of combined DataFrame (all 5 projects)
  - Label distribution: count and percentage of FAIL vs PASS
  - Per-repo breakdown table: rows, FAIL count, FAIL rate, feature count

  **2. Missing value heatmap:**
  - `seaborn.heatmap` of `df.isnull()` on a sample of 1000 rows (full dataset may be too large to render)
  - Axis labels: columns on x-axis, sample rows on y-axis

  **3. Correlation matrix (top 15 by absolute correlation with `label`):**
  - Compute `df[numeric_cols].corrwith(df['label']).abs().sort_values(ascending=False).head(15)`
  - Render as a seaborn heatmap or bar chart
  - Exclude: `commit_sha`, `test_id`, `timestamp`, `feature_source`, `label` from correlation computation

  **4. Mutual information score ranking (all features vs `label`):**
  - Use `sklearn.feature_selection.mutual_info_classif`
  - Render as a horizontal bar chart, all features, sorted descending by MI score
  - Exclude same non-feature columns as in section 3

  **5. Distribution plots for top-5 features by MI score:**
  - For each of the top 5 features: histogram + KDE plot, coloured by `label` (0 vs 1)
  - Use `seaborn.histplot(hue='label', kde=True)`

  **6. `days_since_last_fail` vs `failure_rate_30d` scatter plot:**
  - x-axis: `days_since_last_fail`, y-axis: `failure_rate_30d`
  - Points coloured by `label`
  - Exclude sentinel values (rows where `days_since_last_fail=999` or `failure_rate_30d=-1`) from this plot

  **7. Written conclusion cell (Markdown):**
  - Heading: `## Conclusion`
  - Content: "Top 3 most predictive features and why" — 3–5 sentences, grounded in the MI scores and correlation values computed above
  - Explicit statement: "No data leakage detected — all features are computed from records strictly before `as_of_ts`."
  - Note `commit_meta_missing` rate for each project

## Out of Scope
- Model training or cross-validation — Sprint 3
- Feature engineering changes based on EDA findings — those require a backlog entry before being implemented
- Writing conclusions to a separate `.md` file — the notebook cell IS the conclusion artifact

## Implementation Notes
**Loading Parquet files:** load all 5 projects and concatenate:
```python
import glob, pandas as pd
dfs = [pd.read_parquet(p) for p in glob.glob('data/features/*_features.parquet')]
df = pd.concat(dfs, ignore_index=True)
```

**`feature_source` handling:** exclude from all numerical analysis (it is a string audit column). Do not pass to `mutual_info_classif`.

**Sentinel values in MI computation:** `-1` and `999` are valid integer/float values that `mutual_info_classif` will process as-is. Do not impute or drop them before computing MI — they carry signal (cold-start vs warm test).

**Per-repo breakdown table** — use `df.groupby('repo').agg(...)` if a `repo` column is present. If not, derive project name from `commit_sha` prefix or a filename column if FeatureJoiner adds one.

**Cells must be idempotent:** re-running any cell must not change the output or raise an error.

**Notebook execution:** after writing the notebook, execute it fully using:
```bash
jupyter nbconvert --to notebook --execute notebooks/02_eda_features.ipynb --output notebooks/02_eda_features.ipynb
```
The executed output (with cell outputs) is what gets committed.

## Deliverables
- `notebooks/02_eda_features.ipynb` — fully executed (cell outputs present)

## Verification
```bash
# Verify all cells executed without errors (no empty output on a non-empty notebook)
jupyter nbconvert --to script notebooks/02_eda_features.ipynb --stdout | python
# OR re-execute and check exit code:
jupyter nbconvert --to notebook --execute notebooks/02_eda_features.ipynb --output /tmp/check.ipynb && echo "OK"
```

## Definition of Done
- [ ] Notebook exists at `notebooks/02_eda_features.ipynb`
- [ ] All 7 sections present in the specified order
- [ ] All cells executed top-to-bottom without errors (cell outputs present in committed notebook)
- [ ] Missing value heatmap renders (seaborn)
- [ ] Correlation matrix uses top-15 by absolute correlation with `label`
- [ ] MI ranking computed with `sklearn.feature_selection.mutual_info_classif`
- [ ] Distribution plots for top-5 MI features include histogram + KDE coloured by `label`
- [ ] Scatter plot excludes sentinel rows (`days_since_last_fail=999`, `failure_rate_30d=-1`)
- [ ] Written conclusion cell names top 3 most predictive features and explicitly states no data leakage detected
- [ ] `commit_meta_missing` rate documented per project in the notebook
---
