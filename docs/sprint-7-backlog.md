# Sprint 7 Backlog — Dashboard + Full Evaluation

**Duration:** Week 13–14  
**Sprint Goal:** ReactJS dashboard live; full evaluation dataset (72 data points) collected; statistical analysis complete.  
**Phase:** Evaluation & Thesis  
**Effort estimate:** ~58h

---

## Definition of Done

- [ ] Dashboard at `localhost:3000` loads all panels with live data
- [ ] 72 evaluation data points collected (6 strategies × 4 metrics × 3 repos)
- [ ] Wilcoxon signed-rank test p-values documented
- [ ] All thesis plots exported as PNG/PDF in `docs/results/plots/`
- [ ] Failure analysis: ≥ 5 commit examples where model predicted incorrectly, with explanations

---

## Stories

---

### S7-01 · ReactJS dashboard — project setup

**Priority:** High  
**Estimate:** 3h

**Description:**  
Initialise the ReactJS dashboard project with required dependencies and base layout.

**Acceptance Criteria:**
- Project at `dashboard/` created with `npm create vite@latest dashboard -- --template react`
- Dependencies installed: `axios`, `recharts`, `date-fns`
- Base layout: sidebar navigation + main content area
- `npm run dev` starts dashboard at `localhost:3000` without errors
- `axios` base URL configured from `VITE_API_URL` environment variable (default: `http://localhost:8080`)
- Proxy configured in `vite.config.js` for local development: `/api` → Spring Boot at `localhost:8080`

---

### S7-02 · Build History panel

**Priority:** High  
**Estimate:** 5h

**Description:**  
Implement the Build History table showing per-commit prediction accuracy and CI time comparison.

**Acceptance Criteria:**
- Panel component `BuildHistoryPanel.jsx`
- Fetches from Spring Boot endpoint `GET /api/builds?limit=50`
- Table columns:
  - Commit SHA (first 8 chars, links to GitHub)
  - Repository name
  - Timestamp (relative, e.g. "2 hours ago")
  - Tests ranked (count)
  - Actual failures detected (count)
  - APFD (for this commit, formatted to 2 decimal places)
  - Smart CI time (seconds)
  - Full CI time (seconds, if available)
  - Time saved (%)
- Rows with APFD < 0.5 highlighted in amber
- Polling every 30 seconds with `setInterval`

**Spring Boot endpoint required:**
- `GET /api/builds` returns list of `BuildRecord` objects from `build_results` table (add table to SQLite schema)

---

### S7-03 · APFD Trend chart

**Priority:** High  
**Estimate:** 4h

**Description:**  
Implement a time-series line chart showing rolling APFD over the last 30 days.

**Acceptance Criteria:**
- Component `APFDTrendChart.jsx` using `recharts LineChart`
- X-axis: date (daily buckets)
- Y-axis: mean APFD (0.0 – 1.0)
- Three lines: one per repository, colour-coded
- Horizontal reference line at APFD = 0.70 (target threshold, labelled)
- Tooltip shows exact APFD value on hover
- Chart title: "Rolling APFD — Last 30 Days"
- Data fetched from `GET /api/metrics/apfd-trend?days=30`

---

### S7-04 · Time Saved KPI panel

**Priority:** High  
**Estimate:** 4h

**Description:**  
Implement the KPI summary panel showing aggregate time savings.

**Acceptance Criteria:**
- Component `TimeSavedPanel.jsx`
- Displays four KPI cards:
  1. **Total hours saved** (cumulative, since deployment)
  2. **Average time reduction %** (per build)
  3. **Builds today** (count)
  4. **Flaky tests detected** (count, all time)
- Each card shows the metric value prominently and a small sparkline of the last 7 days
- Data fetched from `GET /api/metrics/kpis`
- KPI values are estimated (smart CI time = `avg_duration_ms * stop_after_index / n_tests`)

---

### S7-05 · Model Health panel

**Priority:** Medium  
**Estimate:** 3h

**Description:**  
Implement the model health status panel showing current model metadata and drift status.

**Acceptance Criteria:**
- Component `ModelHealthPanel.jsx`
- Fetches from FastAPI `GET /health` and `GET /drift-status`
- Displays:
  - Model version (e.g. `test-predictor v2`)
  - Last retrain timestamp
  - Current mean PSI score
  - Drift detected badge (green "OK" or amber "DRIFT DETECTED")
  - Top-3 features by PSI value (bar chart, `recharts BarChart`)
- Polling every 60 seconds

---

### S7-06 · Spring Boot dashboard API endpoints

**Priority:** High  
**Estimate:** 5h

**Description:**  
Implement the backend endpoints in Spring Boot that the dashboard consumes.

**Acceptance Criteria:**
- Controller `DashboardController` at `src/main/java/.../DashboardController.java`
- Endpoints:
  - `GET /api/builds?limit=N` → list of last N builds from SQLite `build_results` table
  - `GET /api/metrics/apfd-trend?days=N` → daily APFD aggregated per repo for past N days
  - `GET /api/metrics/kpis` → aggregate KPIs (total hours saved, avg time reduction, builds today, flaky count)
- SQLite schema additions:
```sql
CREATE TABLE build_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_sha      TEXT NOT NULL,
    repo            TEXT NOT NULL,
    timestamp       INTEGER NOT NULL,
    n_tests_total   INTEGER,
    n_tests_run     INTEGER,
    n_failures_actual INTEGER,
    apfd            REAL,
    smart_ci_ms     INTEGER,
    full_ci_ms      INTEGER
);
```
- All endpoints return JSON; empty state returns empty array (not 404)
- Unit tests with H2 in-memory database for SQLite

---

### S7-07 · Full evaluation pipeline execution

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Run the definitive evaluation of all strategies across all three repositories to collect the complete dataset for thesis Chapter 4.

**Acceptance Criteria:**
- Script `scripts/run_full_evaluation.py`
- Evaluates 6 strategies: Random, Alphabetical, MRF, XGBoost, LightGBM, XGBoost+EarlyExit
- Evaluates on 3 repositories: commons-lang, commons-collections, spring-core
- Metrics collected per `(strategy, repo, commit)`: APFD, Precision@10, Precision@20, Recall@20
- Aggregate per `(strategy, repo)`: mean, std, min, max
- Total data points: 6 × 4 × 3 = 72 aggregate cells; raw commit-level data also saved
- All results logged to MLflow experiment `full-evaluation`
- Results saved to:
  - `docs/results/full_evaluation_raw.csv` (one row per commit evaluation)
  - `docs/results/full_evaluation_summary.md` (6×4 table per repo)

**Expected minimum results (sanity check):**
- XGBoost APFD > MRF APFD on all 3 repos
- XGBoost APFD std < 0.15 (stability)

---

### S7-08 · Statistical significance testing

**Priority:** High  
**Estimate:** 5h

**Description:**  
Apply the Wilcoxon signed-rank test to determine whether the ML model's APFD improvement over MRF is statistically significant.

**Acceptance Criteria:**
- Script `scripts/statistical_tests.py` using `scipy.stats.wilcoxon`
- Comparisons tested (per repo):
  1. XGBoost vs MRF
  2. LightGBM vs MRF
  3. XGBoost+EarlyExit vs MRF
- For each comparison: W-statistic, p-value, effect size (Cohen's d)
- Significance threshold: α = 0.05
- Results table saved to `docs/results/statistical_tests.md`:

| Comparison | Repo | W-stat | p-value | Significant? | Effect size |
|------------|------|--------|---------|--------------|-------------|
| XGBoost vs MRF | commons-lang | | | | |
| ... | | | | | |

- Interpretation notes added: what the p-value means for each RQ answer

---

### S7-09 · All thesis plots generation

**Priority:** High  
**Estimate:** 6h

**Description:**  
Generate all figures that will appear in the thesis, formatted for print quality.

**Acceptance Criteria:**
- Script `scripts/generate_plots.py` produces all plots in `docs/results/plots/`
- All plots: 300 DPI PNG + PDF, 6×4 inch figure size, Arial font, no gridlines except x-axis
- Required plots:

| Filename | Type | Content |
|----------|------|---------|
| `apfd_comparison_bar.png` | Grouped bar chart | APFD per strategy per repo |
| `early_exit_tradeoff.png` | Scatter with annotations | Time reduction % vs FNR % |
| `apfd_over_time.png` | Line chart | APFD trend over test-set commits |
| `feature_importance_shap.png` | Horizontal bar | Top-15 features by mean SHAP |
| `drift_psi_bar.png` | Bar chart | PSI per feature at drift simulation |
| `cv_stability_box.png` | Box plot | APFD distribution per fold (5-fold CV) |

- Each plot reviewed: labels readable, legend present, axes labelled with units

---

### S7-10 · Failure analysis

**Priority:** High  
**Estimate:** 5h

**Description:**  
Identify and explain cases where the model made incorrect predictions, providing qualitative insight for the thesis discussion section.

**Acceptance Criteria:**
- Notebook `notebooks/05_failure_analysis.ipynb`
- Identifies ≥ 10 commits from test set where model APFD < 0.5 (worst-case predictions)
- For each: show commit message, changed files, predicted scores vs actual outcomes
- Identifies ≥ 2 common patterns explaining model errors:
  - Pattern examples: first occurrence of a new test, large refactoring, environment-dependent failures
- Identifies ≥ 5 commits where model significantly outperformed MRF (APFD delta > 0.2) — explain why
- Notebook exported as PDF: `docs/results/failure_analysis.pdf`

---

## Sprint 7 — Dependency Map

```
S7-01 (setup) ──→ S7-02 (build history) ──┐
              ──→ S7-03 (APFD trend)    ──┤
              ──→ S7-04 (KPIs)          ──┤── all depend on S7-06 (Spring Boot API)
              ──→ S7-05 (model health)  ──┘

S7-07 (full eval) ──→ S7-08 (stat tests) ──→ S7-09 (plots)
               └──→ S7-10 (failure analysis)
```

---

## Milestone M4 Checklist (end of Sprint 7)

- [ ] `docs/results/full_evaluation_summary.md` exists with 72 data points
- [ ] `docs/results/statistical_tests.md` shows p-values for all 3 comparisons × 3 repos
- [ ] All 6 plots exist in `docs/results/plots/` at 300 DPI
- [ ] `docs/results/failure_analysis.pdf` exists
- [ ] Dashboard loads at `localhost:3000` with non-empty data

> After M4: numbers are frozen. Chapter 4 of the thesis is written from these results only.  
> No re-evaluation or recollection of data from Sprint 8 onward.

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Full evaluation takes > 8 hours | Medium | Medium | Run 3 repos in parallel; checkpoint intermediate results to CSV so partial results are not lost |
| Wilcoxon test not significant (p > 0.05) | Medium | High | Report result honestly; explain in thesis discussion (small dataset, high variance); cite literature on similar findings |
| Dashboard data empty (no builds recorded) | Medium | Medium | Populate `build_results` table from evaluation run data; dashboard is for presentation, not accuracy |
| Evaluation results contradict thesis claims | Low | High | Adjust claim wording in proposal; discuss with GVHD; scope reduction is acceptable |
