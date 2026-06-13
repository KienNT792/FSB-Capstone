# Sprint 1 — Decisions Log

Records key architecture and data decisions made during Sprint 1.
Each entry follows the ADR-lite format below.

---

## Decision 1 — RTPTorrent as primary dataset (replacing mvn test replay)

**Date:** 2026-05-01  
**Status:** Decided

**Context:** Original plan was to replay CI history via `mvn test` on Apache Commons repositories. Preliminary audit found that failures in those repos are predominantly caused by Maven environment issues (JDK version mismatch, missing plugins, network-dependent tests), not test logic. This would introduce label noise that invalidates the failure prediction model.

**Decision:** Use RTPTorrent (Mattis et al., MSR 2020) as the primary dataset. This is a published, peer-reviewed collection of 20 Java projects with real TravisCI build results, pre-computed baselines, and `patches.csv` for commit-level feature extraction.

**Rationale:** Eliminates environment noise. Provides reproducible ground truth. Enables direct comparison with published baselines (matrix-naive, matrix-conditional-prob). Reduces setup from weeks to hours.

**Consequences:** Feature extraction reads from DuckDB (loaded from CSVs), not live Maven runs. Git repos are cloned read-only for metadata only. Sprint 2 `CommitFeatureExtractor` sources file lists from `file_changes` table (`patches.csv`), not from `git diff`.

---

## Decision 2 — Project selection threshold lowered from ≥2% to ≥1%

**Date:** 2026-05-10  
**Status:** Decided

**Context:** Original backlog set failure rate threshold at ≥2%. After running `select_rtp_projects.py` against the full 20-project corpus, only 3 projects qualified: deeplearning4j (7.76%), wicket-bootstrap (21.16%), jade4j (19.61%). These 3 projects are not diverse enough to support thesis claim of evaluation across "diverse Java CI ecosystems". The two projects sling and sonarqube, previously assumed to qualify, both fell below 2%.

**Decision:** Lower threshold to ≥1%. Final 5 selected projects: wicket-bootstrap (21.16%), jade4j (19.61%), deeplearning4j (7.76%), adamfisk@LittleProxy (1.61%), thinkaurelius@titan (1.25%).

**Rationale:** Provides diversity across project size (10K–138K LOC), domain (UI framework, graph DB, networking, DL, template engine), and build volume (374–1110 builds). Sensitivity analysis at ≥2% subset reported in thesis Appendix A.

**Consequences:** titan duration features (avg 68.5s per TC) excluded from cross-project feature comparison due to outlier TC time. LittleProxy test set small (~117 builds at 80/20 split) — results reported with high-variance caveat. Thesis proposal Sections 3.1, 3.3, 5.1, 5.4 updated to reflect 5 projects and 1% threshold.

---

## Decision 3 — timestamp column populated in Phase 2, job_sequence as fallback

**Date:** 2026-05-20  
**Status:** Decided

**Context:** `load_rtp_dataset.py` was shipping `timestamp = None` for all rows because the git resolution code (`git.Repo(path).commit(sha).committed_date`) was documented in the backlog but not implemented. The `tr_all_built_commits.csv` file contains only `tr_job_id` and `git_commit_id` — no timestamp column. Timestamps must be resolved via `git log` after repos are cloned.

**Decision:** Phase 1 (current): load all rows with `timestamp = NULL`. Phase 2 (S2-00, Sprint 2): implement `add_timestamps.py` to resolve `committed_date` from cloned repos and `UPDATE test_runs` in place. Fallback: `job_sequence` column (`DENSE_RANK` on numeric `job_id` per project) used by `temporal_split` when `timestamp IS NULL`.

**Rationale:** Unblocks Sprint 1 close-out without requiring all 5 repos to be cloned before loader can run. Phase 2 gate (≥70% coverage per project) must pass before S2-01 and S2-02 are started.

**Consequences:** `temporal_split` in S3-02 must split per-project independently, not on merged dataframe. SHA-disjoint assertion replaces timestamp monotonicity assertion. S2-02 author features use `job_sequence` fallback when `timestamp NULL` and set `author_feature_fallback=1` flag.

---

## Sprint 1 Retrospective

**Date:** 2026-06-12  
**Actual duration:** ~6 weeks (2026-05-01 → 2026-06-12)  
**Planned duration:** 2 weeks

**Root causes of ~3× overrun:**

1. **S2-00 full-scope instead of pilot** — the original backlog called for a pilot-only timestamp resolution on `jade4j`. The decision was made mid-sprint to resolve all 5 projects at once. This was the right call (100% SHA coverage on all projects), but it was unplanned scope that consumed ~1 additional week.

2. **GitPython → batched CLI rewrite** — the original `add_timestamps.py` used GitPython per-SHA lookup, which proved too slow for `deeplearning4j` (>5 min) and failed on orphaned commits in blobless clones. Diagnosing and rewriting to batched `git log --all` + `git show` fallback consumed another ~1 week.

3. **Blobless clone edge cases** — `jade4j` is an archived repo; its commit objects are not reachable from any current ref. This required a second pass with `git show` per SHA and added unanticipated investigation time.

**Carry-forward actions:**

- Set a hard mid-sprint checkpoint at day 7 of each sprint. If no first deliverable exists, re-scope immediately, do not wait until end of sprint.
- If a script approach changes (e.g., library swap), treat it as a new story and log it before implementing; untracked rewrites are the primary source of invisible time loss.
- S2-00 is now fully closed; do not revisit timestamp resolution unless a coverage regression is detected.

---

## Decision 4 - timestamp resolution uses batched Git CLI lookup

**Date:** 2026-06-12  
**Status:** Decided

**Context:** The original `scripts/add_timestamps.py` implementation used GitPython commit lookup one SHA at a time. This created high per-SHA subprocess latency and made `deeplearning4j@deeplearning4j` impractically slow. The repository was cloned with `--filter=blob:none`; all required commit objects existed locally, but many were not reachable from refs, so `git log --all` alone did not cover every RTPTorrent SHA.

**Decision:** Resolve timestamps with local Git CLI calls:

1. Use `git log --all --format=%H %ct` once per repository for reachable commits.
2. Use `git show --no-patch --format=%H %ct` for unresolved SHAs that exist as orphaned/unreachable objects.
3. Batch fallback `git show` calls in chunks of 200 SHAs to avoid the Windows command-line length limit.

**Rationale:** This keeps timestamp enrichment deterministic and local while removing GitPython per-SHA overhead. It also handles blobless clone object stores where commits exist but are not reachable from any current ref.

**Consequences:** Timestamp enrichment now passes for all selected projects at 100% distinct-SHA coverage. Rows with `commit_sha IS NULL` still cannot be timestamped and must use `job_sequence` fallback or be filtered explicitly.

---

## MSE_Thesis_Proposal.docx — Verified Status (2026-06-12)

- **Section 3.1 / Phase 1 deliverables:** Correctly states "5 projects, build count, failure rate ≥1%". OK.
- **Section 3.3 (dataset selection):** Correctly states "five projects qualify: wicket-bootstrap 21.16%, jade4j 19.61%, deeplearning4j 7.76%, LittleProxy 1.61%, titan 1.25%" with ≥1% threshold and sensitivity analysis note for ≥2% in Appendix A. OK.
- **Section 5.1 / RQ table:** Correctly states "5 RTPTorrent projects (failure rate ≥1%; sensitivity analysis at ≥2% in Appendix A)". OK.
- **SQLite → DuckDB in .docx: completed manually.** Two instances patched (Section 3.3 criterion (1) and Architecture table Feature Store row). No further action required on the .docx.

---

## Decision 5 — feature_source is an audit column, excluded from model inputs

**Date:** 2026-06-12  
**Status:** Decided

**Context:** S2-02 and S2-07 require a column `feature_source` (`'timestamp'` | `'job_sequence'`) to track which ordering path was used per row and to assert that the fallback rate per project matches the raw null `commit_sha` fraction. The question arose whether to include this column in the model feature matrix.

**Decision:** `feature_source` is an audit/validation column only. It is retained in the output Parquet for traceability but is explicitly excluded from the `X` matrix passed to model training, alongside `commit_sha`, `test_id`, `label`, and `timestamp`.

**Rationale:** `feature_source` correlates with project identity: `adamfisk@LittleProxy` has ~30% `job_sequence` fallback rows while `neuland@jade4j` has ~0.1%. Including it as a model feature risks the model learning a project-identity proxy rather than a semantic CI signal. This would violate the per-project temporal split assumption and inflate cross-project generalization claims in the evaluation.

**Consequences:** `FeatureJoiner` (S2-05) must exclude `feature_source` from the `X` matrix at construction time. `validate_features` (S2-07) checks `feature_source` distribution against the null `commit_sha` baseline but must not count it toward the ≥20 feature column requirement.

---

## Decision 6 — S2-00 timestamp gate passed for Sprint 2 feature extraction

**Date:** 2026-06-12  
**Status:** Decided

**Context:** S2-00 requires a per-project SHA-resolution decision before commit and author features are implemented. The gate is distinct-SHA coverage for rows with non-NULL `commit_sha`; rows where `commit_sha IS NULL` are structurally untimestamp-able and remain on `job_sequence` fallback.

**Decision:** All five selected projects pass the S2-00 gate and are marked `TIMESTAMP_OK`.

| Project | Resolved SHAs | Eligible Rows | Timestamped Rows | SHA Coverage | Row Coverage | Status |
|---|---:|---:|---:|---:|---:|---|
| `adamfisk@LittleProxy` | 262 / 262 | 10,974 | 10,974 | 100.00% | 69.58% | TIMESTAMP_OK |
| `deeplearning4j@deeplearning4j` | 871 / 871 | 14,625 | 14,625 | 100.00% | 94.30% | TIMESTAMP_OK |
| `l0rdn1kk0n@wicket-bootstrap` | 823 / 823 | 38,905 | 38,905 | 100.00% | 80.67% | TIMESTAMP_OK |
| `neuland@jade4j` | 314 / 314 | 35,851 | 35,851 | 100.00% | 99.90% | TIMESTAMP_OK |
| `thinkaurelius@titan` | 382 / 382 | 39,243 | 39,243 | 100.00% | 87.09% | TIMESTAMP_OK |

**Rationale:** Distinct-SHA coverage is 100% for every selected project, so S2-01 and S2-02 can proceed for all projects. LittleProxy row coverage is below 70% because 30.42% of its rows have `commit_sha IS NULL`; this is a source-data gap, not a timestamp-resolution failure.

**Consequences:** Feature extraction should use timestamp ordering for rows with resolved commits and `job_sequence` fallback for structurally null-SHA rows. No project-level `JOB_SEQUENCE_FALLBACK` caveat is needed for S2-00.

---

## Decision 7 — line-count churn is audited when blobless clones cannot provide diffs

**Date:** 2026-06-12  
**Status:** Decided

**Context:** S2-01 asks for `lines_added`, `lines_deleted`, and `churn_total` from git diffs. The local selected-project clones are sufficient for commit metadata and timestamps, but most are blobless/object-filtered clones. Attempting patch or numstat diffs can trigger lazy fetches from GitHub, which is not a reliable local, reproducible source during the Sprint 2 pipeline.

**Decision:** The feature pipeline disables lazy fetch for diff collection. If a diff cannot be computed from local objects, the line-count churn values are set to zero and the row is marked with `commit_diff_missing=1`. File-list churn features from RTPTorrent `patches.csv` remain populated from the `file_changes` table.

**Rationale:** This preserves reproducibility and avoids fabricating line counts. RTPTorrent `patches.csv` contains changed file paths only (`sha`, `name`), not line additions/deletions, so there is no alternate committed source for numeric line churn in the current workspace.

**Consequences:** Sprint 3 model training must treat `lines_added`, `lines_deleted`, and `churn_total` as low-confidence in this artifact snapshot and should consider excluding them or using `commit_diff_missing` as an audit filter. Any future attempt to recover line churn must use full local clones with blobs available and regenerate the feature parquet files.

---

## Decision 9 — S2-08 EDA notebook executed; M1 milestone closed

**Date:** 2026-06-12  
**Status:** Decided

**Decision:** S2-08 (`notebooks/02_eda_features.ipynb`) executed cleanly end-to-end. Top-5 features by mutual information confirmed: `days_since_last_fail` (0.2365), `failure_rate_90d` (0.2002), `failure_rate_30d` (0.1888), `consecutive_passes` (0.1622), `failure_rate_7d` (0.1558). All top-5 are test-history features. M1 milestone declared closed.

**Rationale:** MI ranking and correlation-with-label ranking agree on the top features, providing cross-validation. No data leakage detected — all history features computed strictly before `as_of_ts`; rows without `commit_sha` use `job_sequence` fallback (tracked via `feature_source` column).

**Consequences:** M1 milestone closed. Feature pipeline frozen — no changes to extractor logic from Sprint 3 onward unless a critical bug is found (see Pending entry on `commit_diff_missing` for `deeplearning4j` below).

> **Cross-reference:** `docs/architecture-snapshot.md` Sprint 2 output summary table reflects actual pipeline output. Update architecture-snapshot.md to reflect feature pipeline status change from "Placeholder" to "Implemented".

---

## Pending Decisions

| Date | Issue | Status | Interim Action | Resolution Trigger |
|---|---|---|---|---|
| 2026-06-12 | `commit_diff_missing = 100%` for `deeplearning4j@deeplearning4j` (local clone is blobless; line-count diffs require lazy-fetching blobs). Affects `lines_added`, `lines_deleted`, `churn_total` for this project only. `commit_meta_missing` for this project is only 5.7% — metadata is fine, only line-count diffs are affected. | PENDING — Option A (unblob clone, ~2–4h) vs Option B (document as limitation, no code change) | Treat churn features (`lines_added`, `lines_deleted`, `churn_total`) for `deeplearning4j` as unreliable/audit-flagged. Does not block Sprint 3 — these features rank outside top-5 by MI (≤0.054). | Revisit if Sprint 4 SHAP analysis shows churn features have significant importance for `deeplearning4j` specifically, OR if `deeplearning4j` APFD is anomalously low relative to other projects. Default to Option B if no trigger fires by end of Sprint 4. |

---

## Known Drift To Resolve

- Sprint 2 feature pipeline (`data_pipeline.py`) is now implemented and validated — update `docs/architecture-snapshot.md` accordingly (mark feature pipeline row as "Implemented").

---

## Resolved Drift

### SonarSource "high failure rate" claim in sprint-1-backlog.md Risks table

**Resolved:** 2026-06-12

**Original text (committed, now corrected):** The Risks table in `docs/backlog/sprint-1-backlog.md` stated:
> "Failure rate < 2% in all candidate projects | Low | High | Dataset has 20 projects — expand selection; `deeplearning4j` and `SonarSource` have known high failure rates"

**Correction:** `SonarSource@sonarqube` has a measured failure rate of 0.03% across 17M+ test rows — one of the lowest in the corpus. It does not qualify at any of the thresholds used (2% or 1%). The claim was an incorrect assumption made before the full-corpus scan was run. The Risks row was updated to reflect the actual post-scan outcome: threshold was lowered to ≥1%, 5 projects were selected, and the risk is marked resolved.
