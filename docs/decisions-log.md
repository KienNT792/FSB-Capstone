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
