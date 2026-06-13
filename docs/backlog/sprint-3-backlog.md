# Sprint 3 Backlog — Baseline + XGBoost

**Duration:** Week 5–6  
**Sprint Goal:** Evaluation framework operational; XGBoost model logged in MLflow with APFD exceeding all baselines.  
**Phase:** Model Development  
**Effort estimate:** ~64h

---

## Definition of Done

- [ ] `evaluation_framework.py` contains `APFDCalculator` validated against a hand-calculated example
- [ ] MLflow experiment `baseline` has 5 runs (Random, Alphabetical, MRF, MatrixNaive, MatrixConditionalProb) with APFD logged per project
- [ ] Published RTPTorrent baselines loaded and cross-validated against own implementation (APFD delta < 0.02)
- [ ] MLflow experiment `xgboost-tuning` has ≥ 50 trials; best model logged as artifact
- [ ] APFD of best XGBoost model > APFD of MRF baseline on ≥ 1 project
- [ ] SHAP summary plot generated for top-10 features

---

## Stories

---

### S3-01 · APFDCalculator implementation

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement the `APFDCalculator` class that computes the Average Percentage of Faults Detected (APFD) metric given a ranked list of tests and their actual outcomes.

**Acceptance Criteria:**
- Class located at `src/evaluation/apfd.py`
- Method `compute(ranked_test_ids: list[str], fault_matrix: dict[str, int]) -> float`
  - `ranked_test_ids`: ordered list of test IDs (index 0 = runs first)
  - `fault_matrix`: `{test_id: 1}` for tests that actually failed, `{test_id: 0}` for passing
  - Returns APFD in range `[0.0, 1.0]`; returns `0.0` if no faults exist
- APFD formula:
  ```
  APFD = 1 - (sum(rank_of_first_failing_test_i for each fault_i) / (n_tests * n_faults)) + (1 / (2 * n_tests))
  ```
- Hand-calculated validation test in `tests/test_apfd.py`:
  - 5 tests, 2 failing (positions 1 and 3 in ranking) → verified expected value
  - All failing tests ranked last → APFD near 0
  - All failing tests ranked first → APFD near 1
- Method `compute_precision_at_k(ranked_test_ids, fault_matrix, k) -> float` also implemented
- Method `compute_recall_at_k(ranked_test_ids, fault_matrix, k) -> float` also implemented

---

### S3-02 · Time-aware train/test split

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Implement the dataset splitter that partitions `full_features.parquet` into training and test sets using temporal ordering, preventing data leakage.

**Acceptance Criteria:**
- Function `temporal_split(df: pd.DataFrame, train_ratio: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]` in `src/evaluation/splitter.py`
- **Per-project assertion (G2):** hard-assert `df["repo"].nunique() == 1` at entry; caller must filter `full_features.parquet` by `repo` before calling.
- **Split unit: `job_sequence` (G1):** all rows sharing a `job_sequence` value belong to the same CI job and land in the same split. `job_sequence` is always non-null (DENSE_RANK on `job_id`); NULL `commit_sha` rows are distributed proportionally into train and test — never excluded.
- **Ordering:** sort by `job_sequence` ascending (per-project, contiguous 1…N); earliest `floor(train_ratio × max_job_sequence)` sequences → train; remainder → test.
- **No-leakage assertion (job_id-disjoint):**
  ```python
  train_seqs = set(train_df['job_sequence'].unique())
  test_seqs  = set(test_df['job_sequence'].unique())
  assert train_seqs.isdisjoint(test_seqs), \
      f"Leakage: {len(train_seqs & test_seqs)} job_sequences appear in both splits"
  ```
- Function logs split stats: `"<repo> — Train: {n_jobs} jobs, {n_rows} rows ({n_nonnull_sha} non-null SHAs). Test: {n_jobs} jobs, {n_rows} rows ({n_nonnull_sha} non-null SHAs). Split at seq {threshold}/{max_seq}."`
- Unit tests in `tests/test_splitter.py`:
  - job_id-disjoint: verify no `job_sequence` value appears in both splits (primary correctness test)
  - Per-repo assertion: mixed-repo DataFrame raises `ValueError`
  - `job_sequence` ordering correctness: train contains only earlier sequences than test
  - NULL `commit_sha` rows retained in both splits (G1 correctness)
  - Two rows sharing `job_sequence=N` both land in the same set
  - Edge case: 2-job DataFrame still produces non-empty train and test

---

### S3-03 · Baseline strategy implementations

**Priority:** Critical  
**Estimate:** 12h

**Description:**  
Implement five baseline test ordering strategies as a common interface for comparison against the ML model. The two matrix-based strategies mirror the algorithms documented in the RTPTorrent dataset, allowing direct cross-validation against the published baseline CSVs.

**Acceptance Criteria:**
- Base class `BaseStrategy` with method `rank(test_ids: list[str], features: pd.DataFrame) -> list[str]` in `src/evaluation/strategies.py`
- Five concrete implementations:

| Class | Logic | Source |
|-------|-------|--------|
| `RandomOrderStrategy` | Shuffle test list using `random.seed(42)` | — |
| `AlphabeticalOrderStrategy` | Sort test IDs lexicographically | — |
| `MostRecentlyFailedStrategy` | Sort by `days_since_last_fail` ascending; tests with no failure history ranked last | — |
| `MatrixNaiveStrategy` | Build file-test failure matrix `M[f,t]`; score test `t` as `sum(M[f,t] for f in changed_files)` | RTPTorrent `matrix-naive` |
| `MatrixConditionalProbStrategy` | Rank by `P(t\|c) = sum(P(t\|f) for f in c)`; `P(t\|f) = M[t,f] / M[f]` | RTPTorrent `matrix-conditional-prob` |

- `MatrixNaiveStrategy` and `MatrixConditionalProbStrategy` require a historical matrix built from `test_runs` + `file_changes` tables; method `fit(history_df, file_changes_df)` builds the matrix before `rank()` is called
- All strategies return the complete list of test IDs (no filtering)
- Unit tests in `tests/test_strategies.py` verify each strategy on a 10-test fixture dataset
- **Cross-validation test:** for `MatrixNaiveStrategy`, compute APFD on one RTPTorrent project and compare against the published `matrix-naive.csv` baseline; delta must be < 0.02 (confirms correct implementation)

---

### S3-04 · Evaluation runner

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement the evaluation loop that runs a given strategy over the test set and computes aggregate metrics, logging all results to MLflow.

**Acceptance Criteria:**
- Function `evaluate_strategy(strategy, test_df: pd.DataFrame, experiment_name: str) -> dict` in `src/evaluation/runner.py`
- For each unique `job_id` in `test_df` (APFD runner groups by `job_id`, not `commit_sha` — handles NULL `commit_sha` builds as valid evaluation points):
  1. Get `test_ids` and `fault_matrix` for that job
  2. Call `strategy.rank(test_ids, job_features)`
  3. Compute APFD, Precision@10, Precision@20, Recall@20
- Aggregate metrics: mean and std across all jobs
- All metrics logged to MLflow run under `experiment_name`
- Returns dict: `{"apfd_mean": float, "apfd_std": float, "p@10_mean": float, ...}`
- Jobs that have 0 failing tests are excluded from APFD calculation (logged as `skipped_jobs` metric)

---

### S3-05 · Baseline evaluation execution

**Priority:** High  
**Estimate:** 6h

**Description:**  
Execute the evaluation runner for all five baseline strategies on all selected RTPTorrent projects and log results to MLflow.

**Acceptance Criteria:**
- Script `scripts/run_baseline_eval.py` runs all five strategies on all 5 selected projects
- MLflow experiment `baseline` created with 25 runs total (5 strategies × 5 projects)
- Each run tagged with `project` and `strategy` for filtering in UI
- Baseline results table saved to `docs/results/baseline_apfd.md` (one column per project, all 5 selected):

```markdown
| Strategy                | wicket-bootstrap | jade4j | deeplearning4j | LittleProxy* | titan* |
|-------------------------|-----------------|--------|----------------|--------------|--------|
| Random                  | X.XX            | X.XX   | X.XX           | X.XX         | X.XX   |
| Alphabetical            | X.XX            | X.XX   | X.XX           | X.XX         | X.XX   |
| MRF                     | X.XX            | X.XX   | X.XX           | X.XX         | X.XX   |
| Matrix-Naive            | X.XX            | X.XX   | X.XX           | X.XX         | X.XX   |
| Matrix-ConditionalProb  | X.XX            | X.XX   | X.XX           | X.XX         | X.XX   |

\* LittleProxy and titan have failure rate < 2%; results include high-variance caveat.
```

- **Cross-validation row added:** RTPTorrent published `recently-failed` APFD loaded from baseline CSV and compared against own MRF implementation (delta documented)
- Expected ranges (for sanity check): Random ≈ 0.48–0.52, MRF ≈ 0.60–0.70, Matrix strategies ≈ 0.65–0.80

---

### S3-06 · XGBoostTrainer implementation

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement the `XGBoostTrainer` class with a `predict_proba` interface compatible with the evaluation framework.

**Acceptance Criteria:**
- Class located at `src/models/xgboost_trainer.py`
- Method `train(train_df: pd.DataFrame) -> xgb.XGBClassifier`
- No preprocessing pipeline — sentinel values (`-1` for cold-start failure rates, `999.0` for `days_since_last_fail`) are passed as raw numeric features. Tree-based models split on threshold boundaries natively; median-imputing sentinels would conflate cold-start rows with non-sentinel values and degrade `days_since_last_fail` (top-1 MI feature, score 0.2365).
- Class imbalance handled via `scale_pos_weight = neg_count / pos_count`
- Features used: all columns except `[commit_sha, test_id, label, timestamp, feature_source, repo, job_sequence]`
- Method `predict_proba(model, test_df) -> pd.Series` returns failure probability per row
- Method `rank(test_ids, features, model) -> list[str]` returns test IDs sorted by probability descending (highest failure probability first)
- Integrates with `BaseStrategy` interface so it can be passed to `evaluate_strategy()`
- Trained model saved as MLflow artifact `models/xgboost_v1` (no `sklearn.Pipeline` wrapper needed; model receives raw feature DataFrame directly)

---

### S3-06b · RandomForestTrainer implementation

**Priority:** High  
**Estimate:** 3h

**Description:**  
Implement `RandomForestTrainer` with the same interface as `XGBoostTrainer` (S3-06) to add a non-boosting comparison model for RQ1.

**Acceptance Criteria:**
- Class at `src/models/rf_trainer.py`; implements `train()`, `predict_proba()`, `rank()` — identical interface to S3-06.
- No preprocessing pipeline (raw sentinel features, per S3-06 preprocessing decision).
- Class imbalance: `class_weight='balanced_subsample'`.
- Features: identical exclusion set to XGBoost/LightGBM (`[commit_sha, test_id, label, timestamp, feature_source, repo, job_sequence]`).
- Optuna study: 15 trials only — tune `n_estimators`, `max_depth`, `min_samples_leaf`, `max_features`. (Yaraghi et al. 2022 [yaraghi2022]: tuned vs default RF APFDC delta = 0.011 — full 50-trial budget not justified.)
- Trained model saved as MLflow artifact `models/rf_v1`; integrates with `BaseStrategy`.
- Unit test `tests/test_rf_trainer.py`: `rank()` returns correct length, no duplicates.

---

### S3-07 · Optuna hyperparameter tuning for XGBoost

**Priority:** High  
**Estimate:** 8h

**Description:**  
Run a 50-trial Optuna study to find the best XGBoost hyperparameters, with all trials logged to MLflow.

**Acceptance Criteria:**
- Script `scripts/tune_xgboost.py` runs the Optuna study
- Search space:
```python
{
  "n_estimators":    trial.suggest_int("n_estimators", 100, 1000),
  "max_depth":       trial.suggest_int("max_depth", 3, 10),
  "learning_rate":   trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
  "subsample":       trial.suggest_float("subsample", 0.6, 1.0),
  "colsample_bytree":trial.suggest_float("colsample_bytree", 0.6, 1.0),
  "min_child_weight":trial.suggest_int("min_child_weight", 1, 10),
  "gamma":           trial.suggest_float("gamma", 0.0, 1.0),
}
```
- Objective: maximise mean APFD on **train set** using 3-fold `TimeSeriesSplit`
- Each trial logged to MLflow experiment `xgboost-tuning` with all hyperparams and CV APFD
- Best trial parameters saved to `docs/results/xgboost_best_params.json`
- Best model retrained on full train set and logged as MLflow artifact `models/xgboost_v1`

---

### S3-08 · XGBoost evaluation & SHAP analysis

**Priority:** High  
**Estimate:** 8h

**Description:**  
Evaluate the best XGBoost model on the held-out test set and produce SHAP-based feature importance analysis.

**Acceptance Criteria:**
- Script `scripts/evaluate_xgboost.py` runs evaluation using `evaluate_strategy()` on test split
- Results logged to MLflow experiment `xgboost-eval` with tag `model=xgboost_v1`
- APFD comparison table updated in `docs/results/baseline_apfd.md` to include XGBoost row
- SHAP analysis:
  - `shap.TreeExplainer` used (not `KernelExplainer`)
  - Summary bar plot (mean absolute SHAP) saved to `docs/results/shap_summary.png`
  - Top-10 features with SHAP values recorded in `docs/results/feature_importance.md`
- XGBoost APFD must exceed MRF baseline on ≥ 1 repo to proceed; if not, log findings and open risk item

---

### S3-09 · Evaluation framework unit tests

**Priority:** High  
**Estimate:** 6h

**Description:**  
Complete unit test coverage for all evaluation framework components.

**Acceptance Criteria:**
- `tests/test_apfd.py`: ≥ 6 test cases including edge cases (zero faults, all faults, single test)
- `tests/test_splitter.py`: ≥ 6 test cases — job_id-disjoint assertion, per-repo assertion (ValueError on multi-repo input), job_sequence ordering correctness, NULL commit_sha rows retained in both splits, same-job rows stay together, edge case (2-job DataFrame)
- `tests/test_strategies.py`: ≥ 3 test cases per strategy
- `tests/test_runner.py`: ≥ 3 test cases with mocked MLflow to avoid real logging in CI
- `pytest tests/` exits 0

---

## Sprint 3 — Dependency Map

```
S3-01 (APFD) ──┐
S3-02 (split)  ──┤
S3-03 (baselines, 5 strategies) ──┴──→ S3-04 (runner) ──→ S3-05 (baseline eval, 5 strategies × 5 projects)
                                                       └──→ S3-06 (XGBoost) ──→ S3-06b (RandomForest) ──→ S3-07 (tuning: XGBoost + RF) ──→ S3-08 (eval + SHAP)
S3-09 (tests) ← depends on S3-01 through S3-06b
```

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| APFD implementation bug invalidates all results | Medium | Critical | Hand-calculate expected value for at least 2 test cases before trusting automated results |
| XGBoost APFD < MRF (no improvement) | Medium | High | Check for data leakage first; then review feature quality in EDA; add `test_file_touched` as forced feature |
| Optuna tuning takes > 4 hours | Low | Medium | Reduce to 30 trials; use early pruning with `MedianPruner` |
| `TimeSeriesSplit` produces empty folds | Low | Medium | Verify minimum fold size ≥ 100 rows before running tuning |

---

## Appendix A — Sensitivity Analysis Plan

**Scope:** Results for `adamfisk@LittleProxy` (1.19% failure rate, ~117 test-set commits) and `thinkaurelius@titan` (1.46%, ~191 test-set commits) must be reported with explicit uncertainty quantification due to small failure counts. Standard point-estimate APFD is unreliable in these conditions.

### Required analyses for LittleProxy and titan

**1. Bootstrap confidence intervals for APFD**

For each evaluated strategy on LittleProxy and titan:
- Resample test-set commits with replacement, 1000 iterations, `random_state=42`.
- Compute APFD per bootstrap replicate.
- Report: mean APFD ± 95% CI (2.5th and 97.5th percentile of bootstrap distribution).
- Implementation: `scripts/bootstrap_apfd.py`, results appended to `docs/results/baseline_apfd.md` under `*` footnote columns.

**2. ≥2% threshold subset (thesis Appendix A)**

Re-run the full evaluation pipeline (baselines + XGBoost) on the 3-project subset that qualifies under the original ≥2% threshold: `wicket-bootstrap`, `jade4j`, `deeplearning4j`.

Purpose: Allows readers to assess whether the 1% threshold expansion meaningfully changed conclusions, as stated in Decision 2.

Report format:
```
Table A.1 — APFD at ≥2% threshold (3 projects)
[same columns as main Table X but wicket-bootstrap, jade4j, deeplearning4j only]
```

**3. Reporting caveats**

In the main results table, LittleProxy and titan columns must be annotated with:
> `*` Failure rate < 2%; APFD estimates have high variance. See Appendix A for bootstrap CIs.

Do not claim statistical significance for APFD differences on these two projects without bootstrap CI overlap check.

**Timeline:** Bootstrap analysis is part of S3-08 (XGBoost evaluation). The ≥2% subset run requires no additional data pipeline work — filter parquet by `repo` at evaluation time.
