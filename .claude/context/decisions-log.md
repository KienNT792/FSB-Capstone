# Design Decisions Log

Last updated: 2026-06-13 (G1/G2 resolved)

## Decided

| Date | Decision | Rationale | Consequences |
|------|----------|-----------|--------------|
| 2026-05-01 | Use RTPTorrent as the primary dataset instead of replaying `mvn test`. | Apache Commons replay produced environment-noise labels from JDK/plugin/network failures. RTPTorrent is published, reproducible CI history. | Pipelines read CSV/DuckDB ground truth. Git clones are metadata sources only. |
| 2026-05-10 | Lower project selection threshold from `>= 2%` to `>= 1%` and evaluate 5 projects. | Only 3 projects qualified at `>= 2%`, which was too narrow for the thesis diversity claim. | Selected projects are wicket-bootstrap, jade4j, deeplearning4j, LittleProxy, and titan. Report low-failure projects with caveats. |
| 2026-05-20 | Load `timestamp = NULL` first, then enrich from cloned Git repos. | `tr_all_built_commits.csv` does not include timestamps; resolving commit dates requires cloned repos. | Sprint 1 loader remains reproducible from CSVs; timestamp enrichment is a separate step. Rows without `commit_sha` use `job_sequence` fallback. |
| 2026-06-12 | Resolve timestamps with batched Git CLI calls instead of GitPython per-SHA lookup. | GitPython per-SHA lookup was too slow for large repos; blobless clones can contain unreachable commit objects. | `scripts/add_timestamps.py` uses `git log --all` plus batched `git show` fallback. All 2,652 non-null SHAs across 5 selected projects are timestamped. |
| 2026-06-13 | **G1 — `temporal_split` split unit is `job_sequence`, not `commit_sha`.** NULL `commit_sha` rows (8.5–30.4% per project) span the entire build timeline across all quintiles — they are NOT clustered at the start. 150–203 distinct NULL-SHA job_ids per project contain real failures (0.3–19.9% fail rate). Cannot exclude them from test sets. | `job_sequence` is always non-null (0 NULLs), contiguous DENSE_RANK, proven proxy for temporal order. Grouping by `commit_sha` would collapse all NULL-SHA rows into one untreatable group. | `temporal_split(project_df, train_ratio)` splits on `job_sequence` threshold. Assertion: `job_id-disjoint` (no job_id in both sets). APFD runner groups test_df by `job_id`, not `commit_sha`. Backlog S3-02 "SHA-disjoint assertion" is corrected to "job_id-disjoint". |
| 2026-06-13 | **G2 — `temporal_split` is single-project only; callers filter by `repo` first.** Five selected projects have overlapping date ranges (titan 2012–2014, LittleProxy 2012–2016, etc.). Cross-project temporal ordering is semantically undefined: a 2013-07 titan build and a 2013-07 LittleProxy build are independent events from different test suites. | APFD is per test suite (per `job_id`). Cross-project mixing would create unequal train fractions and has no valid split semantics. EDA notebook always uses `df.groupby('repo')` as primary grouping. | `temporal_split` hard-asserts `df["repo"].nunique() == 1`. S3-04 runner pattern: `for repo in projects: project_df = full_df[full_df["repo"] == repo]; train, test = temporal_split(project_df, 0.8)`. Never call `temporal_split(full_features_df, ...)` directly. |
| 2026-06-13 | Sync S3-02 backlog text to G1/G2 (job_sequence / job_id-disjoint / per-repo split). | Backlog text still described commit_sha-based split, contradicting G1 decision (2026-06-13). Re-sync found this drift unresolved. | S3-02 acceptance criteria and unit test descriptions rewritten; S3-04 runner spec updated to group by `job_id`. |
| 2026-06-13 | Remove `SimpleImputer(median)` + `StandardScaler()` from S3-06 / S4-01 / S3-06b. | Median-imputing sentinel `-1`/`999` conflates cold-start rows with real values; `days_since_last_fail` (sentinel=999) is top-1 MI feature (0.2365) — imputation must not corrupt it. | All tree-based trainers receive raw sentinel-coded features; no scaling needed (scale-invariant). Feature exclusion list updated: `[commit_sha, test_id, label, timestamp, feature_source, repo, job_sequence]`. |
| 2026-06-13 | Add Random Forest as 3rd RQ1 comparison model (S3-06b), reduced Optuna budget (15 trials). | Yaraghi et al. 2022 [yaraghi2022]: RF outperformed LambdaMART/MART/RankBoost/ListNet/CA for APFDC; cheap to add via existing `BaseStrategy` interface. Full 50-trial budget unjustified (tuned vs default APFDC delta = 0.011). | S4 DoD → 8 strategies; S4-04 comparison table gains RF row; S8-09 slide 7 updated to include RF; `yaraghi2022` already in references.bib. |
| 2026-06-13 | M1 closure — Sprint 2 feature parquets produced and validated for all 5 projects. | `scripts/data_pipeline.py` ran successfully for all 5 projects; `data/scripts/assemble_full_features.py` concatenated them into `data/features/full_features.parquet` (160,454 rows × 37 cols) and passed `validate_features()`. | Feature quality snapshot: see table below. Git clones live under `data/git-repos/<owner>@<repo>/` (not `data/repos/`); all are blobless (blob:none). deeplearning4j clone is 122.69 MiB across 5 packs. |

### M1 Feature Quality Snapshot (2026-06-13)

| Project | Shape | Label dist (% positive) | commit_meta_missing % | parse_fail % |
|---|---|---|---|---|
| adamfisk@LittleProxy | (15772, 37) | 1.2% | 30.4% | 1.3% |
| deeplearning4j@deeplearning4j | (15509, 37) | 6.0% | 5.7% | 6.0% |
| l0rdn1kk0n@wicket-bootstrap | (48228, 37) | 22.5% | 19.5% | 2.5% |
| neuland@jade4j | (35887, 37) | 3.7% | 0.1% | 0.0% |
| thinkaurelius@titan | (45058, 37) | 1.5% | 12.9% | 8.3% |

`commit_meta_missing %` = rows where git commit object was unavailable (blobless miss or NULL commit_sha); all commit/author features zero-filled. `parse_fail %` = `dependency_parse_failed` mean; test source not found or `javalang` parse error.

## Working Rules From Decisions

- Do not reintroduce Maven replay as a data-labeling step.
- Do not move RTPTorrent source CSVs out of `data/repos/rtp-torrent/`.
- Feature extraction should read from DuckDB tables loaded from RTPTorrent.
- Commit/file-change features should use RTPTorrent `-patches.csv` data via `file_changes`.
- Cross-validation and temporal splits must be per-project and time/order aware.
- `temporal_split` splits by `job_sequence` threshold (NOT `commit_sha` groups); assert `job_id-disjoint` across train/test.
- `temporal_split` is single-project only: callers must filter `full_features.parquet` by `repo` first; function hard-asserts `df["repo"].nunique() == 1`.
- APFD runner groups test_df by `job_id` (not `commit_sha`) — handles NULL-SHA builds as valid evaluation points.
- Any result on LittleProxy or titan needs an explicit low-failure-rate/high-variance caveat.
- Rows without `commit_sha` are real dataset gaps; `job_sequence` is the temporal proxy — never drop these rows from train or test.

## Pending Decisions

| Date | Issue | Status | Interim Action | Resolution Trigger |
|---|---|---|---|---|
| 2026-06-12 | `commit_diff_missing = 100%` for `deeplearning4j@deeplearning4j` (local clone is blobless; line-count diffs require lazy-fetching blobs). Affects `lines_added`, `lines_deleted`, `churn_total` for this project only. `commit_meta_missing` for this project is only 5.7% — metadata is fine, only line-count diffs are affected. | PENDING — Option A (unblob clone, ~2–4h) vs Option B (document as limitation, no code change) | Treat churn features (`lines_added`, `lines_deleted`, `churn_total`) for `deeplearning4j` as unreliable/audit-flagged. Does not block Sprint 3 — these features rank outside top-5 by MI (≤0.054). | Revisit if Sprint 4 SHAP analysis shows churn features have significant importance for `deeplearning4j` specifically, OR if `deeplearning4j` APFD is anomalously low relative to other projects. Default to Option B if no trigger fires by end of Sprint 4. |
| 2026-06-12 | `test_file_touched` and `same_package` have near-zero MI (0.000124 and 0.000193). Root cause: `dependency_parse_failed=1` for 31–98% of rows forces zero-fill. Implementation is correct. | OPEN | Accept low signal; document as data limitation. Optionally ablate from models with high parse-fail rates. | Revisit if parse_fail rate is reduced by switching to a historical-commit blob approach for dependency extraction. |

## Known Drift To Resolve

- Some Sprint 1 plan/backlog text still references `>= 2%` selection and exactly 3 projects. Current decision and generated summary use `>= 1%` and 5 projects.
- S3-02 commit_sha vs job_sequence drift: resolved 2026-06-13 — see Decided table (Sync S3-02 backlog text row).
