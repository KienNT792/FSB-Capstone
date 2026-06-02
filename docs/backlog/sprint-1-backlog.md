# Sprint 1 Backlog — Environment & Ground Truth

**Duration:** Week 1–2  
**Sprint Goal:** Development environment fully operational; RTPTorrent dataset loaded into SQLite and validated.  
**Phase:** Foundation & Data  
**Effort estimate:** ~47 hours

> **Dataset change (v2):** The original approach of replaying CI history via `mvn test` on Apache Commons repos was abandoned — CI failures in those repos are predominantly caused by environment issues (JDK version mismatch, missing Maven plugins, network-dependent tests), not by test logic. The primary dataset is now **RTPTorrent** (Mattis et al., MSR '20): a published, peer-reviewed collection of TravisCI build results for 20 Java projects, available at `references/rtp-torrent-v11/`.

---

## Definition of Done

- [ ] MLflow tracking UI accessible at `localhost:5000`
- [ ] `test_history.db` contains ≥ 10,000 `(job, test)` records loaded from RTPTorrent CSVs, with `outcome`, `duration_ms`, `job_sequence`; `timestamp` may be NULL pending S2-00
- [ ] Exactly 3 RTPTorrent projects confirmed and documented: `deeplearning4j@deeplearning4j`, `l0rdn1kk0n@wicket-bootstrap`, `neuland@jade4j`
- [ ] Failure ratio documented per selected project (imbalance report)
- [ ] Literature notes (2–3 pages) covering ROCKET, Bertolino 2020, Elsner 2021, RTPTorrent (Mattis 2020)

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
javalang==0.13.0   # optional: used only for import-overlap features in S2-04
pandas==2.2.2
pyarrow==16.0.0
evidently==0.4.22
pytest==8.2.0
```

> **Note:** `gitpython` is retained for reading git commit metadata (message, author, diff) from cloned repos. `javalang` is retained for dependency feature extraction (S2-04) but is now optional — RTPTorrent repos are from the Java 8/11 era so parse failure rate is low. Neither package is used to run Maven or replay CI.

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

### S1-03 · RTPTorrent project selection & git repository acquisition

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Select ≥ 3 projects from the RTPTorrent dataset with sufficient failure signal, then clone the corresponding GitHub repositories. Repos are cloned **read-only** for git metadata extraction only — no Maven execution.

**Acceptance Criteria:**
- Script `scripts/select_rtp_projects.py` reads all `<project>.csv` files under `references/rtp-torrent-v11/rtp-torrent/`
- For each project, computes:
  - Total `(job, test)` pairs
  - Overall failure rate = `(failures + errors) / count` aggregated across all jobs
  - Number of distinct TravisCI job IDs (≈ number of builds)
- Selection criteria:
  - Failure rate ≥ 2%
  - Number of builds ≥ 100
  - Has an associated `-patches.csv` (required for commit features)
- Summary table written to `data/rtp-project-summary.md` and printed to stdout
- **Minimum 3 projects selected**; target 5 for broader evaluation
- Corresponding GitHub repos cloned under `data/repos/` using URLs parsed from the `<user>@<project>` directory names:
  - e.g., `apache@sling` → `https://github.com/apache/sling`
- Each clone verified: `git log --oneline | wc -l` returns ≥ 100
- `data/repos/README.md` records: project name, GitHub URL, build count, failure rate

**Verified selection results (actual data, not estimates):**

Full scan of all 20 projects against criteria (failure rate ≥ 2%, builds ≥ 100, has -patches.csv):

| Project | Rows | Jobs | Fail% | Passes? |
|---------|------|------|-------|---------|
| `deeplearning4j@deeplearning4j` | 15,511 | 1,038 | 6.0% | **YES** |
| `l0rdn1kk0n@wicket-bootstrap` | 51,169 | 1,110 | 21.2% | **YES** |
| `neuland@jade4j` | 35,887 | 932 | 3.7% | **YES** |
| All others | — | — | < 2% | NO |

**These 3 projects are the confirmed selection for all sprints.**

Note on `l0rdn1kk0n@wicket-bootstrap` (21.2% fail rate): the high rate reflects a period of sustained test instability in this repo, not a single flaky test. This is a feature, not a bug — high failure signal reduces class imbalance. The project is **included**.

Note on original candidates: `apache@sling` (0.49%), `SonarSource@sonarqube` (0.06%), `Graylog2@graylog2-server` (0.03%) all fail the 2% threshold. The backlog note "deeplearning4j and SonarSource have known high failure rates" was incorrect for SonarSource.

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

### S1-04b · Literature review — RTPTorrent (MSR 2020)

**Priority:** High  
**Estimate:** 2h

**Description:**  
Read the RTPTorrent paper and document dataset structure, collection methodology, and scope. This is required both for thesis citation and for understanding data limitations.

**Acceptance Criteria:**
- Citation added to `docs/literature/references.bib`:
```bibtex
@inproceedings{rtptorrent,
  author    = {Mattis, Toni and Rein, Patrick and D{\"u}rsch, Falco and Hirschfeld, Robert},
  title     = {{RTPTorrent}: An Open-source Dataset for Evaluating Regression Test Prioritization},
  booktitle = {17th International Conference on Mining Software Repositories},
  series    = {MSR '20},
  year      = {2020},
  doi       = {10.1145/3379597.3387458}
}
```
- Notes appended to `docs/literature/supporting-notes.md`:
  - Date range of collected builds
  - Projects included and their characteristics
  - Known limitations (e.g., only class-level test granularity, no method-level outcomes)
  - How Elsner 2021 used this dataset (for positioning)

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

### S1-06 · RTPTorrent CSV loader — SQLite ingestion pipeline

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Build a script that reads RTPTorrent CSV files and loads them into SQLite using a schema compatible with the rest of the feature extraction pipeline. This replaces the Maven replay approach entirely.

**Data mapping:**
- `<project>.csv`: `travisJobId`, `testName`, `duration`, `failures`, `errors`, `skipped` → `test_runs` table
- `tr_all_built_commits.csv`: `tr_job_id` → `sha` mapping → populates `commit_sha` in `test_runs`
- `<project>-patches.csv`: `sha`, `name` → `file_changes` table (used in Sprint 2 by `CommitFeatureExtractor`)

**Acceptance Criteria:**
- Script `scripts/load_rtp_dataset.py` accepts `--projects` (comma-separated list of `<user>@<project>` names) and `--rtp-path` arguments
- SQLite schema:
```sql
CREATE TABLE test_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    repo         TEXT NOT NULL,
    job_id       TEXT NOT NULL,         -- TravisCI job ID (numeric string)
    commit_sha   TEXT,                  -- joined from tr_all_built_commits.csv; NULL if unmapped
    test_id      TEXT NOT NULL,         -- Java class name (testName column)
    test_index   INTEGER,               -- original position in TravisCI run order (run_index in CSV)
    outcome      TEXT NOT NULL,         -- PASS | FAIL | ERROR | SKIPPED
    duration_ms  REAL,                  -- duration * 1000; NULL if CSV duration field is empty
    timestamp    INTEGER,               -- Unix epoch from git commit date; NULL until --add-timestamps run
    job_sequence INTEGER,               -- DENSE_RANK on CAST(job_id AS INTEGER); fallback sort when timestamp IS NULL
    run_count    INTEGER,               -- count column from CSV
    UNIQUE(repo, job_id, test_id)
);
CREATE TABLE file_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo        TEXT NOT NULL,
    commit_sha  TEXT NOT NULL,
    file_path   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_test_runs_commit   ON test_runs(commit_sha);
CREATE INDEX IF NOT EXISTS idx_test_runs_test_id  ON test_runs(test_id);
CREATE INDEX IF NOT EXISTS idx_file_changes_commit ON file_changes(commit_sha);
```
- Outcome derivation: `failures > 0 OR errors > 0` → `FAIL`; `skipped > 0 AND count = skipped` → `SKIPPED`; else → `PASS`
- **`duration_ms` is explicitly nullable**: `square@okhttp` has 100% empty duration fields in the source CSV — these rows are loaded with `duration_ms = NULL`. This is expected and acceptable. Projects with > 10% null `duration_ms` are flagged in the summary output (does not block ingestion).
- **`timestamp` two-phase population**:
  - Phase 1 (this script): `timestamp = NULL` for all rows. `job_sequence` is populated using `DENSE_RANK() OVER (ORDER BY CAST(job_id AS INTEGER))` within each repo and is the ordering fallback for Sprint 2 temporal split when `timestamp` is NULL.
  - Phase 2 (`--add-timestamps` flag, requires S1-03 repos cloned): resolves `timestamp` by looking up `committed_date` from the cloned git repo for each `commit_sha`. Rows whose `commit_sha` is not found in the local clone remain NULL.
  - **`timestamp` is commit-level, not job-level**: multiple `job_id` values from the same commit (matrix builds) share the same `timestamp`. Sprint 2 temporal split MUST split on `commit_sha` groups, not individual rows, to avoid data leakage.
- Script is idempotent: re-running skips already-loaded `(repo, job_id, test_id)` triples
- Prints summary after load: total rows, failure rate, null-commit-sha count, null-duration count per project

**`--add-timestamps` implementation notes (Phase 2):**
- Requires repos cloned under `data/repos/` by S1-03
- For each distinct `commit_sha` in `test_runs`, call `git.Repo(repo_path).commit(sha).committed_date`
- Batch-update: `UPDATE test_runs SET timestamp = ? WHERE repo = ? AND commit_sha = ?`
- Skip if SHA not found in local clone (remains NULL); log count of unresolved SHAs
- After update, print: `"timestamp coverage: {n_resolved}/{n_total} distinct SHAs ({pct:.1f}%)"`

**Implementation notes:**
- Use `csv.DictReader` for all CSV parsing (not pandas — avoids memory spikes on 17M-row SonarSource CSV)
- Join `tr_all_built_commits.csv` on `tr_job_id` to get `commit_sha`; some jobs may map to multiple SHAs (parallel matrix builds) — use the first SHA for the job
- `job_sequence` is computed post-load via a single SQL UPDATE using a window function equivalent in SQLite:
  ```sql
  WITH ranked AS (
      SELECT id, DENSE_RANK() OVER (PARTITION BY repo ORDER BY CAST(job_id AS INTEGER)) AS seq
      FROM test_runs WHERE repo = ?
  )
  UPDATE test_runs SET job_sequence = ranked.seq
  FROM ranked WHERE test_runs.id = ranked.id;
  ```

---

### S1-07 · Ground truth validation & imbalance report

**Priority:** High  
**Estimate:** 5h

**Description:**  
Validate the contents of `test_history.db` loaded from RTPTorrent and produce a report characterising dataset quality, class distribution, and suitability for model training.

**Acceptance Criteria:**
- Notebook `notebooks/01_ground_truth_validation.ipynb` created and fully executed
- Report covers per selected project:
  - Total `(job, test)` pairs loaded
  - Jobs with `commit_sha = NULL` (unmapped) — flag if > 20%
  - Failure rate = `COUNT(outcome='FAIL') / COUNT(*)`
  - Top 10 most frequently failing tests
  - Distribution of `duration_ms` (min, median, p95, max)
  - Date range of builds (earliest to latest timestamp)
- Cross-validation against RTPTorrent `<project>-offenders.csv`: verify that jobs flagged as "failure-introducing" have matching `outcome=FAIL` rows in `test_runs`
- If failure rate < 2% on any project → that project is dropped from selection; substitute from remaining candidates
- Total records across all selected projects ≥ 10,000

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
S1-01 (env) ──────────────────────────────────────────┐
S1-02 (mlflow) ───────────────────────────────────────┤
S1-03 (project selection + git clone) ──→ S1-06 (RTPTorrent loader) ──→ S1-07 (validation)
S1-04 (ROCKET) ──┐
S1-04b (RTPTorrent paper) ──┤
S1-05 (papers)  ──┴──→ Milestone: literature notes done
S1-08 (scaffold) ──→ (all future stories depend on this)
```

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Many jobs in RTPTorrent have no SHA mapping in `tr_all_built_commits.csv` | Medium | Medium | Retain unmapped rows; use job-level ordering for temporal split; resolve SHA for ≥ 70% of jobs |
| Failure rate < 2% in all candidate projects | Low | High | Dataset has 20 projects — expand selection; `deeplearning4j` and `SonarSource` have known high failure rates |
| Git clone fails for archived/moved repos | Medium | Low | Use Wayback Machine or dataset-provided archived mirror links (noted in dataset readme for `deeplearning4j`) |
| `javalang` parse fails on some Java syntax | Low | Low | RTPTorrent repos are 2014–2018 era (Java 8/11); parse failure rate expected < 5%; wrap in try/except |
