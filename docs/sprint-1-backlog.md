# Sprint 1 Backlog — Environment & Ground Truth

**Duration:** Week 1–2  
**Sprint Goal:** Development environment fully operational; CI ground truth dataset exists on disk.  
**Phase:** Foundation & Data  
**Effort estimate:** ~65 hours

---

## Definition of Done

- [ ] MLflow tracking UI accessible at `localhost:5000`
- [ ] `test_history.db` contains ≥ 5,000 `(commit, test)` records with `outcome`, `duration_ms`, `timestamp`
- [ ] Failure ratio documented per repository (imbalance report)
- [ ] Literature notes (2–3 pages) covering ROCKET, Bertolino 2020, Elsner 2021

---

## Stories

---

### S1-01 · Python environment setup

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Create an isolated Python environment with all required ML and data libraries pinned to specific versions.

**Acceptance Criteria:**
- `pyenv` installed; Python 3.11 set as local version inside project directory
- `requirements.txt` lists all packages with pinned versions
- `pip install -r requirements.txt` completes without errors in a clean virtualenv
- `python -c "import xgboost, lightgbm, mlflow, fastapi, gitpython, javalang, evidently"` runs without import errors

**Required packages (with versions):**
```
xgboost==2.0.3
lightgbm==4.3.0
scikit-learn==1.4.2
optuna==3.6.1
shap==0.44.1
mlflow==2.12.1
fastapi==0.111.0
uvicorn==0.29.0
gitpython==3.1.43
javalang==0.13.0
pandas==2.2.2
pyarrow==16.0.0
evidently==0.4.22
pytest==8.2.0
```

---

### S1-02 · MLflow tracking server setup

**Priority:** Critical  
**Estimate:** 3h

**Description:**  
Run MLflow tracking server and artifact store locally via Docker Compose. All ML experiments in subsequent sprints will log to this server.

**Acceptance Criteria:**
- `docker-compose.yml` defines `mlflow` service with PostgreSQL backend and local artifact store
- `docker compose up -d` starts server successfully
- MLflow UI accessible at `http://localhost:5000`
- Creating a test experiment via `mlflow.create_experiment("test")` appears in the UI
- Artifact upload (a small text file) succeeds and is retrievable from UI

**docker-compose.yml spec:**
```yaml
services:
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.12.1
    ports: ["5000:5000"]
    volumes: ["./mlflow-artifacts:/mlflow/artifacts"]
    command: >
      mlflow server
      --backend-store-uri sqlite:///mlflow/mlflow.db
      --default-artifact-root /mlflow/artifacts
      --host 0.0.0.0
```

---

### S1-03 · Target repository acquisition

**Priority:** Critical  
**Estimate:** 3h

**Description:**  
Clone three Java repositories that will serve as the primary dataset. Verify each has sufficient commit history and test infrastructure.

**Acceptance Criteria:**
- All three repos cloned under `data/repos/`
- Each repo verified: `git log --oneline | wc -l` returns ≥ 500
- Maven build verified: `mvn test-compile -q` exits 0 on the latest commit
- Test discovery verified: `mvn test -pl <module> -Dtest=NonExistentTest 2>&1 | grep "No tests"` confirms Surefire is configured
- Summary table recorded in `data/repos/README.md`:

| Repo | Commits | Test count | Maven module |
|------|---------|------------|--------------|
| apache/commons-lang | ? | ? | . |
| apache/commons-collections | ? | ? | . |
| spring-projects/spring-framework | ? | ? | spring-core |

**Target repos:**
```
https://github.com/apache/commons-lang
https://github.com/apache/commons-collections
https://github.com/spring-projects/spring-framework
```

**Fallback repos** (if above have insufficient CI history):
```
https://github.com/google/guava
https://github.com/junit-team/junit5
```

---

### S1-04 · Literature review — ROCKET (ICSE 2023)

**Priority:** High  
**Estimate:** 6h

**Description:**  
Read the full ROCKET paper and extract information directly relevant to this thesis: feature set design, evaluation methodology, and identified limitations.

**Acceptance Criteria:**
- Notes file `docs/literature/rocket-notes.md` created
- Notes cover: (1) exact feature set used, (2) APFD scores reported, (3) dataset characteristics, (4) limitations stated by authors
- Research gap section identifies ≥ 2 gaps this thesis addresses that ROCKET does not

**Notes template:**
```markdown
## ROCKET — Key Findings
### Feature set
### Evaluation setup
### APFD results
### Limitations
### Gap vs this thesis
```

---

### S1-05 · Literature review — supporting papers

**Priority:** High  
**Estimate:** 4h

**Description:**  
Read abstracts and relevant sections of Bertolino 2020 and Elsner 2021. Extract evaluation methodology and metric definitions.

**Acceptance Criteria:**
- Notes file `docs/literature/supporting-notes.md` created
- APFD formula extracted and noted with source citation
- Key differences in methodology between papers noted
- Zotero library created with ≥ 5 entries (ROCKET + 4 supporting papers) exported as `docs/literature/references.bib`

---

### S1-06 · CI history reconstruction pipeline

**Priority:** Critical  
**Estimate:** 20h

**Description:**  
Build a script that replays the CI history of a target repository by checking out each commit and running the test suite, then storing pass/fail outcomes in SQLite.

**Acceptance Criteria:**
- Script `scripts/extract_ci_history.py` accepts `--repo-path` and `--limit` arguments
- For each commit (up to `--limit`, most recent first): checkout → run `mvn test -pl <module> -q` → parse Surefire XML reports → insert rows into SQLite
- SQLite schema:
```sql
CREATE TABLE test_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo        TEXT NOT NULL,
    commit_sha  TEXT NOT NULL,
    test_id     TEXT NOT NULL,        -- fully qualified class#method
    outcome     TEXT NOT NULL,        -- PASS | FAIL | ERROR | SKIPPED
    duration_ms REAL,
    timestamp   INTEGER NOT NULL      -- Unix epoch of commit author date
);
CREATE INDEX idx_commit ON test_runs(commit_sha);
CREATE INDEX idx_test   ON test_runs(test_id);
```
- Commits that fail to compile are logged to `logs/compile_errors.txt` and skipped (not inserted)
- Script is idempotent: re-running skips already-processed commits (check by `commit_sha`)
- Surefire XML parser handles both `<testcase>` with `<failure>` child and bare passing `<testcase>`

**Implementation notes:**
- Use `git.Repo(path).iter_commits(max_count=limit)` for iteration
- Parse Surefire reports from `target/surefire-reports/*.xml` after each test run
- Run with `--limit 200` per repo as initial target (expand later if time allows)

---

### S1-07 · Ground truth validation & imbalance report

**Priority:** High  
**Estimate:** 5h

**Description:**  
Validate the contents of `test_history.db` and produce a report characterising the dataset quality and class distribution.

**Acceptance Criteria:**
- Notebook `notebooks/01_ground_truth_validation.ipynb` created and fully executed
- Report covers per-repo:
  - Total commits processed vs skipped (compile errors)
  - Total `(commit, test)` pairs
  - Failure rate = `COUNT(outcome='FAIL') / COUNT(*)`
  - Top 10 most frequently failing tests
  - Distribution of `duration_ms` (min, median, p95, max)
- If failure rate < 2% on any repo → flag as insufficient signal; note mitigation (expand commit window)
- Total records across all repos ≥ 5,000

---

### S1-08 · Project scaffolding & repository structure

**Priority:** Medium  
**Estimate:** 3h

**Description:**  
Establish the standard directory layout and configuration files that all subsequent work will follow.

**Acceptance Criteria:**
- Repository structure created:
```
project-root/
├── data/
│   ├── repos/          # cloned Java repos
│   └── features/       # parquet files (generated)
├── scripts/
│   ├── extract_ci_history.py
│   └── data_pipeline.py   # placeholder
├── src/
│   ├── features/       # extractor modules
│   ├── models/         # trainer modules
│   ├── serving/        # FastAPI app
│   └── evaluation/     # APFD, metrics
├── notebooks/
├── tests/              # pytest unit tests
├── docs/
│   └── literature/
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```
- `README.md` documents how to: (1) setup environment, (2) run CI history extraction, (3) start MLflow
- `.gitignore` excludes: `data/repos/`, `data/features/`, `mlflow-artifacts/`, `__pycache__/`, `.env`

---

## Sprint 1 — Dependency Map

```
S1-01 (env) ──────────────────────────────────┐
S1-02 (mlflow) ───────────────────────────────┤
S1-03 (repos) ──→ S1-06 (CI history) ──→ S1-07 (validation)
S1-04 (ROCKET) ──┐
S1-05 (papers) ──┴──→ Milestone: literature notes done
S1-08 (scaffold) ──→ (all future stories depend on this)
```

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Maven build flaky on older commits | High | Medium | Catch `subprocess.CalledProcessError`; skip and log; target 80% commit coverage |
| Replay takes > 10 hours per repo | Medium | Medium | Run 3 repos in parallel (separate terminals); limit to 200 commits initially |
| Failure rate < 2% (too few positives) | Low | High | Expand to 500 commits; add `commons-math` or `guava` as 4th repo |
| javalang import fails on Java 17 syntax | Medium | Low | Pin to Java 11 commits using `git log --before=2021-01-01` |
