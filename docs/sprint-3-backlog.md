# Sprint 3 Backlog — Baseline + XGBoost

**Duration:** Week 5–6  
**Sprint Goal:** Evaluation framework operational; XGBoost model logged in MLflow with APFD exceeding all baselines.  
**Phase:** Model Development  
**Effort estimate:** ~64h

---

## Definition of Done

- [ ] `evaluation_framework.py` contains `APFDCalculator` validated against a hand-calculated example
- [ ] MLflow experiment `baseline` has 3 runs (Random, Alphabetical, MRF) with APFD logged per repo
- [ ] MLflow experiment `xgboost-tuning` has ≥ 50 trials; best model logged as artifact
- [ ] APFD of best XGBoost model > APFD of MRF baseline on ≥ 1 repo
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
- Split is based on `timestamp` column: earliest 80% of **unique commits** → train; latest 20% → test
- Split is at commit level, not row level (all tests of a given commit stay together in the same split)
- Validation: `assert train_df['timestamp'].max() < test_df['timestamp'].min()`
- Function logs split stats: `"Train: {n_commits} commits, {n_rows} rows. Test: {n_commits} commits, {n_rows} rows."`
- Unit test verifies no commit SHA appears in both splits

---

### S3-03 · Baseline strategy implementations

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement three baseline test ordering strategies as a common interface for comparison against the ML model.

**Acceptance Criteria:**
- Base class `BaseStrategy` with method `rank(test_ids: list[str], features: pd.DataFrame) -> list[str]` in `src/evaluation/strategies.py`
- Three concrete implementations:

| Class | Logic |
|-------|-------|
| `RandomOrderStrategy` | Shuffle test list using `random.seed(42)` |
| `AlphabeticalOrderStrategy` | Sort test IDs lexicographically |
| `MostRecentlyFailedStrategy` | Sort by `days_since_last_fail` ascending (most recently failed first); tests with no failure history ranked last |

- All strategies return the complete list of test IDs (no filtering)
- Unit tests in `tests/test_strategies.py` verify each strategy on a 10-test fixture dataset

---

### S3-04 · Evaluation runner

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement the evaluation loop that runs a given strategy over the test set and computes aggregate metrics, logging all results to MLflow.

**Acceptance Criteria:**
- Function `evaluate_strategy(strategy, test_df: pd.DataFrame, experiment_name: str) -> dict` in `src/evaluation/runner.py`
- For each unique commit in `test_df`:
  1. Get `test_ids` and `fault_matrix` for that commit
  2. Call `strategy.rank(test_ids, commit_features)`
  3. Compute APFD, Precision@10, Precision@20, Recall@20
- Aggregate metrics: mean and std across all commits
- All metrics logged to MLflow run under `experiment_name`
- Returns dict: `{"apfd_mean": float, "apfd_std": float, "p@10_mean": float, ...}`
- Runs that have 0 failing tests are excluded from APFD calculation (logged as `skipped_commits` metric)

---

### S3-05 · Baseline evaluation execution

**Priority:** High  
**Estimate:** 4h

**Description:**  
Execute the evaluation runner for all three baseline strategies on all three repositories and log results to MLflow.

**Acceptance Criteria:**
- Script `scripts/run_baseline_eval.py` runs all three strategies on all three repos
- MLflow experiment `baseline` created with 9 runs total (3 strategies × 3 repos)
- Each run tagged with `repo` and `strategy` for filtering in UI
- Baseline results table saved to `docs/results/baseline_apfd.md`:

```markdown
| Strategy | commons-lang APFD | commons-collections APFD | spring-core APFD |
|----------|-------------------|--------------------------|-----------------|
| Random   | X.XX              | X.XX                     | X.XX            |
| Alpha    | X.XX              | X.XX                     | X.XX            |
| MRF      | X.XX              | X.XX                     | X.XX            |
```

- Expected ranges (for sanity check): Random ≈ 0.48–0.52, Alphabetical ≈ 0.50–0.55, MRF ≈ 0.60–0.70

---

### S3-06 · XGBoostTrainer implementation

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement the `XGBoostTrainer` class with preprocessing pipeline and a `predict_proba` interface compatible with the evaluation framework.

**Acceptance Criteria:**
- Class located at `src/models/xgboost_trainer.py`
- Method `train(train_df: pd.DataFrame) -> xgb.XGBClassifier`
- Preprocessing pipeline (sklearn `Pipeline`):
  1. `SimpleImputer(strategy='median')` — handles sentinel values (-1, 999) by treating them as missing
  2. `StandardScaler()` — applied to all numeric features
- Class imbalance handled via `scale_pos_weight = neg_count / pos_count`
- Features used: all columns except `[commit_sha, test_id, label, timestamp]`
- Method `predict_proba(model, test_df) -> pd.Series` returns failure probability per row
- Method `rank(test_ids, features, model) -> list[str]` returns test IDs sorted by probability descending (highest failure probability first)
- Integrates with `BaseStrategy` interface so it can be passed to `evaluate_strategy()`
- Trained model and preprocessing pipeline saved together as a single `sklearn.Pipeline` artifact

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
- `tests/test_splitter.py`: ≥ 4 test cases verifying temporal ordering and no-leakage
- `tests/test_strategies.py`: ≥ 3 test cases per strategy
- `tests/test_runner.py`: ≥ 3 test cases with mocked MLflow to avoid real logging in CI
- `pytest tests/` exits 0

---

## Sprint 3 — Dependency Map

```
S3-01 (APFD) ──┐
S3-02 (split)  ──┤
S3-03 (baselines) ──┴──→ S3-04 (runner) ──→ S3-05 (baseline eval)
                                          └──→ S3-06 (XGBoost) ──→ S3-07 (tuning) ──→ S3-08 (eval + SHAP)
S3-09 (tests) ← depends on S3-01 through S3-06
```

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| APFD implementation bug invalidates all results | Medium | Critical | Hand-calculate expected value for at least 2 test cases before trusting automated results |
| XGBoost APFD < MRF (no improvement) | Medium | High | Check for data leakage first; then review feature quality in EDA; add `test_file_touched` as forced feature |
| Optuna tuning takes > 4 hours | Low | Medium | Reduce to 30 trials; use early pruning with `MedianPruner` |
| `TimeSeriesSplit` produces empty folds | Low | Medium | Verify minimum fold size ≥ 100 rows before running tuning |
