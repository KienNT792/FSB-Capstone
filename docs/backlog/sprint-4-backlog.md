# Sprint 4 Backlog — LightGBM + Early Exit + Model Registration

**Duration:** Week 7–8  
**Sprint Goal:** Model v1.0 registered in MLflow Registry; confidence-based early exit validated; flaky test detector operational.  
**Phase:** Model Development  
**Effort estimate:** ~66h

---

## Definition of Done

- [ ] MLflow Model Registry contains model `test-predictor` version `1.0` with status `Production`
- [ ] Full comparison table: 7 strategies × 4 metrics × ≥ 3 projects documented in `docs/results/` (5 baselines + XGBoost + LightGBM)
- [ ] Early exit operating point identified: CI time reduction ≥ 25% at FNR ≤ 5%
- [ ] `flaky_detector.py` with unit tests passing
- [ ] Model Card document created at `docs/model-card.md`

---

## Stories

---

### S4-01 · LightGBMTrainer implementation

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement `LightGBMTrainer` following the same interface as `XGBoostTrainer` to enable a direct comparison.

**Acceptance Criteria:**
- Class located at `src/models/lgbm_trainer.py`
- Implements the same interface as `XGBoostTrainer`: `train()`, `predict_proba()`, `rank()`
- Preprocessing pipeline identical to XGBoost (median imputer + standard scaler)
- Class imbalance handled via `is_unbalance=True` (LightGBM native parameter)
- Features used: identical set to XGBoost for fair comparison
- Trained model saved as sklearn `Pipeline` (same pattern as XGBoost)
- Unit test in `tests/test_lgbm_trainer.py`: verify `rank()` returns a list of the correct length with no duplicates

---

### S4-02 · Optuna hyperparameter tuning for LightGBM

**Priority:** High  
**Estimate:** 6h

**Description:**  
Run a 50-trial Optuna study for LightGBM, mirroring the XGBoost tuning setup.

**Acceptance Criteria:**
- Script `scripts/tune_lgbm.py`
- Search space:
```python
{
  "n_estimators":       trial.suggest_int("n_estimators", 100, 1000),
  "num_leaves":         trial.suggest_int("num_leaves", 20, 200),
  "min_child_samples":  trial.suggest_int("min_child_samples", 5, 100),
  "learning_rate":      trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
  "feature_fraction":   trial.suggest_float("feature_fraction", 0.5, 1.0),
  "bagging_fraction":   trial.suggest_float("bagging_fraction", 0.5, 1.0),
  "bagging_freq":       trial.suggest_int("bagging_freq", 1, 10),
  "reg_alpha":          trial.suggest_float("reg_alpha", 0.0, 1.0),
  "reg_lambda":         trial.suggest_float("reg_lambda", 0.0, 1.0),
}
```
- Objective: maximise mean APFD on train set via 3-fold `TimeSeriesSplit`
- All trials logged to MLflow experiment `lgbm-tuning`
- Best params saved to `docs/results/lgbm_best_params.json`
- Best model retrained on full train set and logged as MLflow artifact `models/lgbm_v1`

---

### S4-03 · Cross-validation stability analysis

**Priority:** High  
**Estimate:** 5h

**Description:**  
Evaluate both best models using 5-fold time-series cross-validation to assess prediction stability, not just point-in-time performance.

**Acceptance Criteria:**
- Script `scripts/cross_validate.py` runs `TimeSeriesSplit(n_splits=5)` for both models
- For each fold and each model: compute APFD, Precision@10, Recall@20
- Output: per-fold results table + mean ± std across folds
- Results logged to MLflow runs under experiment `cv-stability`
- A model is considered stable if APFD std across folds < 0.05
- Results saved to `docs/results/cv_results.md`

---

### S4-04 · Full model comparison

**Priority:** Critical  
**Estimate:** 5h

**Description:**  
Produce the definitive comparison table across all strategies and select the official model for registration.

**Acceptance Criteria:**
- Script `scripts/compare_models.py` evaluates all 7 strategies on the held-out test set of all 5 selected projects
- Output comparison table:

| Strategy | APFD | P@10 | P@20 | R@20 | Train time | Inference time (ms/commit) |
|----------|------|------|------|------|------------|---------------------------|
| Random | | | | | — | — |
| Alphabetical | | | | | — | — |
| MRF | | | | | — | — |
| Matrix-Naive | | | | | — | — |
| Matrix-ConditionalProb | | | | | — | — |
| XGBoost | | | | | | |
| LightGBM | | | | | | |

- **Upper bound row (reference only, not a strategy):** `Optimal-Failure` APFD loaded from RTPTorrent `optimal-failure.csv` and added to table as theoretical ceiling

- Inference time measured as: time to score 100 test IDs for one commit on a single CPU core
- **Model selection rule:** choose the model with higher APFD; in case of tie (< 0.01 difference), choose the one with lower inference time
- Selected model documented in `docs/results/model_selection.md` with rationale

---

### S4-05 · MLflow Model Registry — model registration

**Priority:** Critical  
**Estimate:** 3h

**Description:**  
Register the selected model in MLflow Model Registry with proper versioning and stage promotion.

**Acceptance Criteria:**
- Script `scripts/register_model.py` performs registration
- Model registered under name `test-predictor`
- Version `1` promoted to stage `Production`
- Model tags set: `{"algorithm": "xgboost|lgbm", "apfd": "<value>", "training_repo": "<repo_name>", "sprint": "4"}`
- Model loadable via `mlflow.sklearn.load_model("models:/test-predictor/Production")`
- Verification test in `tests/test_model_registry.py`: load model, call `predict_proba()` on a 5-row DataFrame, assert output shape is `(5,)`

---

### S4-06 · Model Card

**Priority:** High  
**Estimate:** 3h

**Description:**  
Write a concise Model Card documenting what the model does, how it was trained, and its known limitations.

**Acceptance Criteria:**
- File at `docs/model-card.md`
- Sections:
  1. **Model description** — task, algorithm, input/output
  2. **Training data** — repos, date range, split method, label distribution
  3. **Evaluation results** — APFD on each repo vs all baselines (table)
  4. **Feature list** — all 25+ features with one-line descriptions
  5. **Limitations** — per-project model only; Java/Maven only; cold-start behaviour; class-level test granularity (RTPTorrent dataset limitation); historical TravisCI data (2014–2018 era)
  6. **How to use** — code snippet showing how to load and call the model

---

### S4-07 · EarlyExitStrategy implementation

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Implement the confidence-based early exit strategy that stops test execution once cumulative failure confidence exceeds a threshold.

**Acceptance Criteria:**
- Class `EarlyExitStrategy` at `src/evaluation/early_exit.py`
- Constructor: `__init__(self, model, threshold: float)`
- Method `get_execution_plan(test_ids: list[str], features: pd.DataFrame) -> dict`
  - Returns `{"ordered_tests": [...], "stop_after": int, "predicted_time_reduction_pct": float}`
  - `stop_after`: index in `ordered_tests` where cumulative predicted-failure probability first exceeds `threshold`
  - `predicted_time_reduction_pct`: `(n_total - stop_after) / n_total * 100`
- Method `evaluate_threshold(threshold: float, test_df: pd.DataFrame) -> dict`
  - Returns `{"threshold": float, "time_reduction_pct": float, "false_negative_rate": float, "n_commits_evaluated": int}`
  - `false_negative_rate`: fraction of commits where at least one actual failure was NOT in the executed subset

**Threshold sweep:**
- Script `scripts/sweep_early_exit.py` evaluates thresholds: `[0.70, 0.75, 0.80, 0.85, 0.90, 0.95]`
- Results saved to `docs/results/early_exit_sweep.md` as a table
- Plot saved to `docs/results/early_exit_tradeoff.png`: x-axis = time reduction %, y-axis = FNR %, each point labelled with threshold
- **Operating point:** threshold where time reduction ≥ 25% AND FNR ≤ 5%; if multiple qualify, pick highest time reduction
- Operating point stored in `config/early_exit_config.json`: `{"threshold": float, "time_reduction_pct": float, "fnr": float}`

**Unit tests** in `tests/test_early_exit.py`:
- `stop_after` is correct for a known 5-test example
- When threshold = 1.0, all tests are executed
- When threshold = 0.0, only 1 test is executed

---

### S4-08 · FlakyTestDetector implementation

**Priority:** Medium  
**Estimate:** 6h

**Description:**  
Implement a detector that flags tests exhibiting flaky behaviour: intermittent failures not correlated with code changes.

**Acceptance Criteria:**
- Class `FlakyTestDetector` at `src/evaluation/flaky_detector.py`
- Method `detect(history_df: pd.DataFrame, min_runs: int = 20) -> pd.DataFrame`
  - Input: `test_history.db` DataFrame with columns `[test_id, outcome, timestamp, commit_sha]`
  - Output: DataFrame with columns `[test_id, flaky_score, is_flaky]`
- Flaky score formula: `duration_variance_percentile * (1 - failure_rate_consistency)`
  - `duration_variance_percentile`: percentile rank of duration variance among all tests
  - `failure_rate_consistency`: correlation between `failure_rate_7d` and `failure_rate_30d` — low correlation = flaky
- A test is flagged `is_flaky = True` if `flaky_score > 0.7` AND `0.05 < failure_rate_30d < 0.5`
- Method `get_flaky_report() -> str` returns a markdown-formatted summary
- Flaky tests are **deprioritized** in ranking (moved to end of list) but not excluded
- Unit tests in `tests/test_flaky_detector.py`:
  - A test that alternates PASS/FAIL every run with stable duration → flagged as flaky
  - A test that always fails → not flagged as flaky
  - A test with < `min_runs` history → not evaluated (marked as `is_flaky = None`)

---

### S4-09 · Sprint 4 integration test

**Priority:** High  
**Estimate:** 4h

**Description:**  
End-to-end integration test that validates the complete model development pipeline from raw features to registered model to early exit plan.

**Acceptance Criteria:**
- Script `scripts/integration_test_sprint4.py`
- Steps verified in sequence:
  1. Load `full_features.parquet`
  2. Run `temporal_split()`
  3. Load model `test-predictor/Production` from MLflow Registry
  4. Run `evaluate_strategy()` → verify APFD > 0.60 (sanity floor)
  5. Run `EarlyExitStrategy` with operating point threshold → verify `stop_after < n_tests`
  6. Run `FlakyTestDetector` → verify output DataFrame has correct schema
- All steps pass without exceptions
- Total runtime ≤ 60 seconds

---

## Sprint 4 — Dependency Map

```
S4-01 (LightGBM) ──→ S4-02 (LGBM tuning) ──┐
                                              ├──→ S4-03 (CV) ──→ S4-04 (comparison) ──→ S4-05 (registry) ──→ S4-06 (model card)
XGBoost (Sprint 3) ────────────────────────┘

S4-07 (EarlyExit) ──→ threshold sweep ──→ config/early_exit_config.json
S4-08 (FlakyDetector)

S4-09 (integration test) ← requires S4-05, S4-07, S4-08
```

---

## Milestone M2 Checklist (end of Sprint 4)

- [ ] `mlflow models list` shows `test-predictor` version 1 at stage `Production`
- [ ] APFD of registered model > MRF baseline on ≥ 1 repo (exact values in `docs/results/baseline_apfd.md`)
- [ ] `config/early_exit_config.json` exists with operating point
- [ ] `pytest tests/` → 0 failures
- [ ] `docs/model-card.md` exists and complete

> After M2: model is frozen. No retraining in Sprint 5–6 unless drift detection triggers it.

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LightGBM APFD identical to XGBoost (< 0.01 diff) | Medium | Low | Document tie; choose by inference time; this is a valid finding |
| Early exit FNR > 5% at any viable threshold | Medium | High | Lower time-reduction claim to 20%; adjust RQ2 wording; document in limitations |
| Flaky test detection produces too many false positives | Low | Low | Raise `flaky_score` threshold to 0.8; this component is not thesis-critical |
| Model Registry API requires MLflow server to be running | Low | Medium | Add health check at start of all scripts that depend on Registry |
