# Sprint 6 Backlog — GitHub Actions + Feedback Loop

**Duration:** Week 11–12  
**Sprint Goal:** End-to-end demo runs on GitHub; drift detection operational with automatic retrain trigger.  
**Phase:** CI Integration  
**Effort estimate:** ~66h

---

## Definition of Done

- [ ] GitHub Action runs on a real push: commit → prediction → reordered test execution, latency ≤ 3 seconds from push to ranked list returned
- [ ] Video or screenshot evidence of smart-CI vs full test suite runtime comparison exists
- [ ] `DriftDetector`: PSI > 0.2 triggers retrain — verified via simulation test
- [ ] Model hot-swap: new model version loaded by FastAPI without service restart
- [ ] End-to-end demo script (`docs/demo-script.md`) runs in 5 minutes

---

## Stories

---

### S6-01 · GitHub Actions custom action

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Create a reusable GitHub Actions composite action that integrates the prediction service into any Java CI workflow.

**Acceptance Criteria:**
- Action defined at `github-action/action.yml`
- Action type: `composite`
- Inputs:

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `api-url` | Yes | — | URL of the FastAPI prediction service |
| `repo-token` | Yes | — | GitHub token for API access |
| `threshold` | No | `0.85` | Early exit confidence threshold |
| `test-output-path` | No | `surefire-includes.txt` | Path to write ranked test list |

- Outputs:

| Output | Description |
|--------|-------------|
| `ranked-tests-file` | Path to generated surefire includes file |
| `estimated-time-reduction` | Predicted CI time reduction percentage |
| `stop-after-index` | Early exit cut-off index |

- Action steps:
  1. Call `POST {api-url}/predict` with current `GITHUB_SHA` and test list from `mvn test --list-tests`
  2. Write `ranked_tests` to `test-output-path`
  3. Set action outputs
- Action script written in bash (`run: shell: bash`)
- `action.yml` includes usage example in `description` field

---

### S6-02 · CI workflow integration on fork repo

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Create a GitHub Actions workflow on a fork of Apache Commons Lang that uses the custom action to run tests in predicted order.

**Acceptance Criteria:**
- Workflow file at `.github/workflows/smart-ci.yml` in the forked repo
- Workflow triggers on `push` to `main`
- Workflow steps:
  1. `actions/checkout`
  2. `actions/setup-java@v4` with Java 11
  3. `mvn test-compile -q` (ensure test classes compiled)
  4. Custom action (using local `github-action/` path or published version)
  5. `mvn test -Dsurefire.includesFile=${{ steps.predict.outputs.ranked-tests-file }}`
- Comparison workflow `.github/workflows/full-ci.yml` runs `mvn test` without reordering (same trigger)
- Both workflows run on the same commit; runtime comparison captured from Actions UI

**Evidence required:**
- Screenshot of both workflow runs side-by-side showing wall-clock time difference
- Saved to `docs/results/sprint6-ci-comparison.png`

---

### S6-03 · Test list discovery from Maven

**Priority:** High  
**Estimate:** 4h

**Description:**  
Implement reliable test ID discovery so the action knows which tests to pass to the prediction API, without hardcoding test class names.

**Acceptance Criteria:**
- Bash script `github-action/scripts/discover_tests.sh`
- Uses `mvn test -Dtest=NonExistentTest --dry-run 2>&1 | grep "Running "` to list compiled test classes
- Alternatively: scan `target/test-classes/` for `.class` files matching `*Test.class` pattern
- Output: newline-delimited list of fully qualified class names
- Handles projects with multiple test source roots
- Script tested on Apache Commons Lang: must discover ≥ 50 test classes

---

### S6-04 · End-to-end latency validation

**Priority:** High  
**Estimate:** 4h

**Description:**  
Measure and document the end-to-end latency from the moment a push event is received to the moment the ranked test list is available to the CI runner.

**Acceptance Criteria:**
- Measurement points instrumented with timestamps:
  - T0: GitHub push event sent
  - T1: Spring Boot webhook received
  - T2: `PredictionClient.predict()` called
  - T3: FastAPI `/predict` response received
  - T4: `surefire-includes.txt` written to disk
- Target: T4 - T0 ≤ 3000ms (3 seconds)
- Results logged to `docs/results/latency-report.md` with percentiles (p50, p95) over ≥ 10 push events
- If T4 - T0 > 3000ms: profile bottleneck, apply fix, re-measure

---

### S6-05 · ResultCollector implementation

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement the component that captures actual test outcomes after each CI run and stores them in the feedback store for drift detection and future retraining.

**Acceptance Criteria:**
- Class `ResultCollector` at `src/serving/result_collector.py`
- Method `collect(commit_sha: str, repo: str, surefire_xml_dir: str) -> int`
  - Parses all Surefire XML reports in `surefire_xml_dir`
  - Inserts new rows into `test_history.db` table `test_runs`
  - Returns count of rows inserted
- Method is idempotent: re-processing the same `commit_sha` does not insert duplicates (check via `(commit_sha, test_id)` unique constraint)
- Spring Boot calls `ResultCollector` endpoint after CI run completes:
  - `POST /collect` accepts `{"commit_sha": str, "repo": str, "surefire_xml_dir": str}`
  - Returns `{"inserted": int}`
- Unit tests in `tests/test_result_collector.py`:
  - Fixture Surefire XML with 3 passing and 1 failing test → 4 rows inserted
  - Re-collecting same commit → 0 rows inserted (idempotent)

---

### S6-06 · DriftDetector implementation

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement the drift detector that monitors changes in feature distribution over time using Population Stability Index (PSI).

**Acceptance Criteria:**
- Class `DriftDetector` at `src/serving/drift_detector.py`
- Constructor: `__init__(self, reference_df: pd.DataFrame, psi_threshold: float = 0.2)`
  - `reference_df`: feature distribution from the training dataset (computed at model registration time)
  - Saved as JSON to `data/reference_distribution.json` during model registration (add to `scripts/register_model.py`)
- Method `compute_psi(current_df: pd.DataFrame) -> dict[str, float]`
  - Computes PSI per feature between `reference_df` and `current_df`
  - PSI formula: `sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))` over 10 equal-width bins
  - Returns `{feature_name: psi_value}` for all numeric features
- Method `is_drift_detected(current_df: pd.DataFrame) -> bool`
  - Returns `True` if mean PSI across top-10 features > `psi_threshold`
- Method `get_drift_report(current_df: pd.DataFrame) -> str`
  - Returns markdown table: feature name, PSI value, drift flag
- `FastAPI` endpoint `GET /drift-status` returns:
  ```json
  {
    "drift_detected": bool,
    "mean_psi": float,
    "features_above_threshold": [{"feature": str, "psi": float}],
    "last_checked": "<ISO timestamp>"
  }
  ```
- Unit tests: synthetic data with known distribution shift → PSI correctly computed; drift flag triggered at correct threshold

---

### S6-07 · RetrainTrigger implementation

**Priority:** High  
**Estimate:** 8h

**Description:**  
Implement the component that automatically triggers model retraining when drift is detected, then registers the new model version.

**Acceptance Criteria:**
- Class `RetrainTrigger` at `src/serving/retrain_trigger.py`
- Method `check_and_trigger(current_df: pd.DataFrame) -> bool`
  - Calls `DriftDetector.is_drift_detected()`
  - If `True`: runs full retraining pipeline, registers new model version, returns `True`
  - If `False`: returns `False`
- Retraining pipeline steps (executed as subprocess or direct call):
  1. `data_pipeline.py` — rebuild `full_features.parquet` with new data from `test_history.db`
  2. `tune_xgboost.py --trials 20` — quick 20-trial retune (not 50, to save time)
  3. `register_model.py` — registers new version, promotes to `Production`
- New model version tagged with `{"triggered_by": "drift_detection", "mean_psi": float}`
- Old `Production` model transitioned to `Archived`
- `POST /trigger-retrain` endpoint (admin use): manually triggers regardless of drift status
- Drift check scheduled: `APScheduler` job runs `check_and_trigger` every 24 hours
- Unit test with mocked `DriftDetector`: PSI above threshold → retraining subprocess called once

---

### S6-08 · Model hot-swap

**Priority:** High  
**Estimate:** 5h

**Description:**  
Enable the FastAPI service to reload a newly registered model version without restarting the process.

**Acceptance Criteria:**
- `POST /reload-model` endpoint on FastAPI (protected by `X-Admin-Token` header)
  - Loads latest `Production` model from MLflow Registry
  - Replaces in-memory model reference (thread-safe using `asyncio.Lock`)
  - Returns `{"previous_version": str, "new_version": str, "reload_latency_ms": float}`
- `RetrainTrigger` calls `POST /reload-model` after registering new model version
- `GET /health` reflects the current loaded model version at all times
- Integration test: register a new mock model version → call `/reload-model` → `/health` shows new version
- Requests in-flight during reload complete using the old model (no interrupted predictions)

---

### S6-09 · Drift simulation test

**Priority:** High  
**Estimate:** 5h

**Description:**  
Verify the full drift → retrain → reload cycle using injected synthetic data.

**Acceptance Criteria:**
- Script `scripts/simulate_drift.py`
- Steps:
  1. Load `full_features.parquet`
  2. Apply artificial distribution shift: multiply `failure_rate_30d` by 3.0 for 30% of rows
  3. Compute PSI → assert PSI > 0.2 for `failure_rate_30d`
  4. Call `DriftDetector.is_drift_detected(shifted_df)` → assert returns `True`
  5. Call `RetrainTrigger.check_and_trigger(shifted_df)` → assert returns `True`
  6. Verify new model version exists in MLflow Registry
  7. Call `POST /reload-model` → verify `/health` returns new version
- All 7 steps logged to console with PASS/FAIL status
- Script exits 0 on full success

---

### S6-10 · End-to-end demo script

**Priority:** High  
**Estimate:** 4h

**Description:**  
Write and validate a step-by-step demo script that can be executed in ≤ 5 minutes to demonstrate the full system to the thesis committee.

**Acceptance Criteria:**
- Document at `docs/demo-script.md`
- Covers:
  1. `docker compose up -d` → both services healthy
  2. Push a commit to the forked Apache Commons Lang repo
  3. GitHub Actions workflow triggered → show smart-CI run in progress
  4. Terminal showing Spring Boot webhook log + FastAPI prediction log
  5. `surefire-includes.txt` displayed (first 5 lines)
  6. smart-CI vs full-CI runtime comparison screenshot
  7. `curl http://localhost:8000/drift-status` → show drift report
  8. `curl -X POST http://localhost:3000/` (dashboard) → show KPIs
- Each step has expected output specified
- Rehearsed and confirmed runnable in ≤ 5 minutes

---

## Sprint 6 — Dependency Map

```
S6-01 (Action) ──→ S6-02 (workflow) ──→ S6-03 (test discovery) ──→ S6-04 (latency)

S6-05 (ResultCollector) ──→ S6-06 (DriftDetector) ──→ S6-07 (RetrainTrigger) ──→ S6-08 (hot-swap)
                                                   └──→ S6-09 (simulation test)

S6-10 (demo script) ← requires S6-02, S6-04, S6-08 complete
```

---

## Milestone M3 Checklist (end of Sprint 6)

- [ ] GitHub Actions workflow run visible at `github.com/{fork}/actions` with ✅
- [ ] `docs/results/sprint6-ci-comparison.png` exists showing time difference
- [ ] `scripts/simulate_drift.py` exits 0 with all 7 steps PASS
- [ ] `docs/demo-script.md` rehearsed and confirmed ≤ 5 minutes

> After M3: no new features. Sprint 7–8 are evaluation and writing only.

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GitHub Actions runner cannot reach local FastAPI service | High | High | Host FastAPI on a reachable server (ngrok tunnel or cloud VM); or use `act` for local Actions testing |
| Drift simulation does not trigger retrain (PSI calculation bug) | Medium | Medium | Validate PSI formula against Evidently AI output on same data |
| Hot-swap causes race condition under load | Low | Low | Use `asyncio.Lock`; this is a thesis prototype, not production system — document as known limitation |
| Retrain takes > 10 minutes on CI machine | Medium | Medium | Reduce retrain to 20 trials; retrain is async and does not block prediction service |
