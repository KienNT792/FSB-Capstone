# Sprint 5 Backlog — Prediction Service + Spring Boot

**Duration:** Week 9–10  
**Sprint Goal:** Prediction API running in Docker; Spring Boot service receives GitHub webhook and returns ranked test list.  
**Phase:** CI Integration  
**Effort estimate:** ~68h

> **Hybrid approach (v2):** Training and evaluation data comes entirely from RTPTorrent (historical). The CI integration demo targets **one live repo** — a fork of `apache/sling` (which is in RTPTorrent) — to demonstrate real GitHub Action → FastAPI → ranked execution flow. The model was trained on historical data from the same project, so predictions are meaningful even for new commits.

---

## Definition of Done

- [ ] `docker compose up` starts FastAPI at `localhost:8000`; Swagger UI accessible
- [ ] `POST /predict` responds in ≤ 2 seconds with ranked test list for a real commit payload
- [ ] Spring Boot service builds successfully; unit test coverage ≥ 80%
- [ ] Webhook handler correctly processes a real GitHub push event payload (verified via ngrok)
- [ ] Integration test: Spring Boot → FastAPI → response parse passes end-to-end

---

## Stories

---

### S5-01 · FastAPI app skeleton

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Create the FastAPI application structure with health check, lifespan model loading, and OpenAPI documentation.

**Acceptance Criteria:**
- App located at `src/serving/app.py`
- Lifespan handler loads model from MLflow Registry on startup:
  ```python
  model = mlflow.sklearn.load_model("models:/test-predictor/Production")
  ```
- `GET /health` returns:
  ```json
  {
    "status": "ok",
    "model_name": "test-predictor",
    "model_version": "1",
    "model_stage": "Production",
    "loaded_at": "<ISO timestamp>"
  }
  ```
- OpenAPI docs at `/docs` (Swagger UI enabled)
- App starts with `uvicorn src.serving.app:app --host 0.0.0.0 --port 8000`
- If MLflow server is unreachable at startup, app logs error and exits with code 1 (fail fast)

---

### S5-02 · Predict endpoint — request/response schema

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Define Pydantic models for the prediction request and response payloads.

**Acceptance Criteria:**
- Schemas in `src/serving/schemas.py`
- Request schema `CommitPayload`:
```python
class CommitPayload(BaseModel):
    repo_path: str          # absolute path on server filesystem
    commit_sha: str         # 40-char hex SHA
    test_ids: list[str]     # fully qualified test IDs to rank
    threshold: float = 0.85 # early exit threshold (overrides config default)
```
- Response schema `PredictionResponse`:
```python
class PredictionResponse(BaseModel):
    ranked_tests: list[str]              # ordered list, highest failure probability first
    scores: list[float]                  # failure probability per test (same order)
    stop_after_index: int                # early exit cut-off index
    estimated_time_reduction_pct: float  # based on stop_after_index / total tests
    flaky_test_ids: list[str]            # tests flagged as flaky (deprioritized)
    model_version: str
    prediction_latency_ms: float
```
- Input validation: `commit_sha` must match regex `^[0-9a-f]{40}$`; `test_ids` must be non-empty
- Invalid input returns HTTP 422 with descriptive error message

---

### S5-03 · Predict endpoint — feature extraction and scoring

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Implement the `POST /predict` endpoint that extracts features for the incoming commit in real-time and returns a ranked test list.

**Acceptance Criteria:**
- Endpoint at `POST /predict` in `src/serving/app.py`
- Processing pipeline:
  1. Validate `CommitPayload`
  2. Load git repo from `repo_path` using `gitpython` (repo must be cloned locally)
  3. Look up file changes for this commit: first from `file_changes` table (SQLite); fall back to live git diff if not found (new commits not in historical data)
  4. Extract commit-level features using `CommitFeatureExtractor`
  5. Load last 90 days of test history from SQLite at `data/test_history.db` (read-only)
  6. For each test ID in `test_ids`: extract `TestHistoryFeatureExtractor` features + `DependencyFeatureExtractor` features
  7. Assemble feature DataFrame (same schema as training data)
  8. Call `model.predict_proba(feature_df)[:, 1]` to get failure probabilities
  9. Apply `FlakyTestDetector` → move flaky tests to end of ranked list
  10. Apply `EarlyExitStrategy` with request `threshold`
  11. Return `PredictionResponse`
- Total latency ≤ 2000ms for up to 500 test IDs
- Latency measured and returned in `prediction_latency_ms`
- If `repo_path` does not exist on server: return HTTP 400 `{"error": "repo_not_found"}`
- If commit SHA not found in repo: return HTTP 400 `{"error": "commit_not_found"}`

**Performance note:** Test history lookup must be batched — one SQL query for all test IDs, not N queries.

---

### S5-04 · Docker containerisation

**Priority:** Critical  
**Estimate:** 5h

**Description:**  
Package the FastAPI service as a Docker image and update `docker-compose.yml` to include it alongside MLflow.

**Acceptance Criteria:**
- `Dockerfile` at `src/serving/Dockerfile`:
  - Base image: `python:3.11-slim`
  - Copies `requirements.txt` and installs dependencies
  - Copies `src/` and `data/` into container
  - Exposes port 8000
  - `CMD ["uvicorn", "src.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]`
- `docker-compose.yml` updated with `predictor` service:
  - Depends on `mlflow` service
  - Mounts `./data` as volume at `/app/data` (so SQLite and repos are accessible)
  - Environment variable `MLFLOW_TRACKING_URI=http://mlflow:5000`
- `docker compose up` starts both services without errors
- `curl http://localhost:8000/health` returns HTTP 200 from host machine
- Image build time ≤ 3 minutes on a standard laptop

---

### S5-05 · FastAPI integration test

**Priority:** High  
**Estimate:** 5h

**Description:**  
Write integration tests that call the running FastAPI service with a real commit from Apache Commons Lang and verify the response.

**Acceptance Criteria:**
- Test file `tests/integration/test_predict_endpoint.py`
- Requires: Docker services running (skip tests if `localhost:8000` is unreachable)
- Test cases:
  1. `test_health_returns_ok`: `GET /health` → status 200, `"status": "ok"`
  2. `test_predict_returns_ranked_list`: `POST /predict` with a known commit → `ranked_tests` length equals input `test_ids` length
  3. `test_predict_score_ordering`: scores in response are in descending order
  4. `test_predict_stop_after_within_bounds`: `stop_after_index` ≤ len(`ranked_tests`)
  5. `test_predict_invalid_sha_returns_422`: commit SHA = `"abc"` → HTTP 422
  6. `test_predict_latency_under_2s`: response time < 2000ms
- Tests use a fixture commit SHA hardcoded from `apache/sling` history (one of the RTPTorrent projects cloned in S1-03)

---

### S5-06 · Spring Boot project setup

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Create the Spring Boot CI Integration Service project with required dependencies and base configuration.

**Acceptance Criteria:**
- Project at `ci-integration-service/` (separate Maven project)
- Spring Boot 3.x with dependencies: `spring-boot-starter-web`, `spring-boot-starter-validation`, `spring-boot-starter-test`, `spring-retry`
- `application.yml`:
```yaml
predictor:
  api-url: http://localhost:8000
  timeout-ms: 5000

webhook:
  github-secret: ${GITHUB_WEBHOOK_SECRET}
```
- `mvn clean package -q` exits 0
- Main class `CiIntegrationServiceApplication` starts without errors

---

### S5-07 · GitHub webhook receiver

**Priority:** Critical  
**Estimate:** 8h

**Description:**  
Implement the webhook endpoint that receives GitHub push events, validates the HMAC signature, and extracts commit metadata.

**Acceptance Criteria:**
- Controller `WebhookController` at `src/main/java/.../WebhookController.java`
- `POST /webhook/github` accepts raw JSON body with header `X-Hub-Signature-256`
- HMAC-SHA256 signature validation:
  - Read `GITHUB_WEBHOOK_SECRET` from environment
  - Compute `HMAC-SHA256(secret, raw_body)`
  - Compare with header value using constant-time comparison (`MessageDigest.isEqual`)
  - Return HTTP 401 if signature mismatch
- Parse GitHub push event JSON:
  - Extract: `repository.full_name`, `after` (commit SHA), `head_commit.modified` (changed files)
  - Map to internal `CommitEvent` record
- On valid event: log `"Received push event for commit {sha[:8]} in {repo}"`
- Return HTTP 200 immediately (async processing in subsequent tasks)
- Unit tests with `MockMvc`:
  - Valid signature → HTTP 200
  - Invalid signature → HTTP 401
  - Missing signature header → HTTP 400
  - Non-push event type → HTTP 200 (ignored gracefully)

---

### S5-08 · PredictionClient

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Implement the HTTP client that calls the FastAPI prediction service from Spring Boot.

**Acceptance Criteria:**
- Class `PredictionClient` at `src/main/java/.../PredictionClient.java`
- Uses Spring's `RestClient` (Spring Boot 3.2+) or `WebClient`
- Method `predict(CommitEvent event, List<String> testIds) -> PredictionResponse`
- Maps `CommitEvent` + `testIds` to `CommitPayload` JSON and `POST`s to `{predictor.api-url}/predict`
- Timeout configured from `predictor.timeout-ms` property
- Retry: 2 retries with 500ms delay on connection timeout (using `spring-retry`)
- Maps JSON response to `PredictionResponse` record with fields: `rankedTests`, `stopAfterIndex`, `estimatedTimeReductionPct`
- If FastAPI is unreachable after retries: throws `PredictorUnavailableException` (caller handles fallback)
- Unit test with WireMock:
  - Successful call → response mapped correctly
  - Timeout → retries 2× then throws `PredictorUnavailableException`
  - HTTP 500 from predictor → throws `PredictionFailedException`

---

### S5-09 · Test list reordering & Surefire config generation

**Priority:** High  
**Estimate:** 6h

**Description:**  
Implement the component that converts a ranked test list into a Maven Surefire-compatible configuration for ordered execution.

**Acceptance Criteria:**
- Class `SurefireConfigGenerator` at `src/main/java/.../SurefireConfigGenerator.java`
- Method `generate(PredictionResponse prediction, Path outputDir) -> Path`
  - Creates file `{outputDir}/surefire-includes.txt`
  - File contains one test class name per line, in ranked order
  - Only tests up to `stopAfterIndex` are included (early exit applied)
- Method `generateFullOrder(PredictionResponse prediction, Path outputDir) -> Path`
  - Same but includes all tests (for comparison runs)
- Output file format example:
  ```
  org.apache.commons.lang3.StringUtilsTest
  org.apache.commons.lang3.ArrayUtilsTest
  ...
  ```
- This file is consumed by Maven via: `mvn test -Dsurefire.includesFile=surefire-includes.txt`
- Unit tests verify: correct ordering, correct cutoff at `stopAfterIndex`, no duplicate entries

---

### S5-10 · Spring Boot unit test completion

**Priority:** High  
**Estimate:** 6h

**Description:**  
Achieve ≥ 80% line coverage across all Spring Boot components.

**Acceptance Criteria:**
- `mvn test` exits 0 with all tests passing
- JaCoCo coverage report generated: `mvn jacoco:report`
- Overall line coverage ≥ 80% (excluding generated code and `Application` main class)
- Coverage report screenshot saved to `docs/results/sprint5-coverage.png`
- Components covered: `WebhookController`, `PredictionClient`, `SurefireConfigGenerator`

---

## Sprint 5 — Dependency Map

```
S5-01 (app skeleton) ──→ S5-02 (schemas) ──→ S5-03 (predict endpoint) ──→ S5-04 (Docker) ──→ S5-05 (integration test)

S5-06 (SB setup) ──→ S5-07 (webhook) ──┐
                    S5-08 (client)  ──┤──→ S5-09 (surefire gen) ──→ S5-10 (coverage)
```

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Real-time feature extraction > 2s for large test suites | Medium | High | Batch SQL queries; cache commit diff result; profile with `cProfile` if latency is high |
| GitHub webhook format differs from expected | Low | Medium | Test with ngrok + real push event before implementing parser |
| MLflow model not loadable from Docker container | Medium | Medium | Mount mlflow-artifacts volume into container; test image locally before integration |
| Spring Boot `RestClient` version compatibility | Low | Low | Pin Spring Boot to 3.2.x; use `RestTemplate` as fallback if needed |
