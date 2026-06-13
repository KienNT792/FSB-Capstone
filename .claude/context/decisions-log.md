# Design Decisions Log

Last updated: 2026-06-13

This file is the compact project-memory version of design decisions. The longer Sprint 1 record is in `docs/decisions-log.md`.

## Decided

| Date | Decision | Rationale | Consequences |
|------|----------|-----------|--------------|
| 2026-05-01 | Use RTPTorrent as the primary dataset instead of replaying `mvn test`. | Apache Commons replay produced environment-noise labels from JDK/plugin/network failures. RTPTorrent is published, reproducible CI history. | Pipelines read CSV/DuckDB ground truth. Git clones are metadata sources only. |
| 2026-05-10 | Lower project selection threshold from `>= 2%` to `>= 1%` and evaluate 5 projects. | Only 3 projects qualified at `>= 2%`, which was too narrow for the thesis diversity claim. | Selected projects are wicket-bootstrap, jade4j, deeplearning4j, LittleProxy, and titan. Report low-failure projects with caveats. |
| 2026-05-20 | Load `timestamp = NULL` first, then enrich from cloned Git repos. | `tr_all_built_commits.csv` does not include timestamps; resolving commit dates requires cloned repos. | Sprint 1 loader remains reproducible from CSVs; timestamp enrichment is a separate step. Rows without `commit_sha` use `job_sequence` fallback. |
| 2026-06-12 | Resolve timestamps with batched Git CLI calls instead of GitPython per-SHA lookup. | GitPython per-SHA lookup was too slow for large repos; blobless clones can contain unreachable commit objects. | `scripts/add_timestamps.py` uses `git log --all` plus batched `git show` fallback. All 2,652 non-null SHAs across 5 selected projects are timestamped. |
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
- Split by commit groups where possible; avoid leaking future test history into feature rows.
- Any result on LittleProxy or titan needs an explicit low-failure-rate/high-variance caveat.
- Rows without `commit_sha` are real dataset gaps; use `job_sequence` fallback or filter them with a documented rationale.

## Known Drift To Resolve

- Some Sprint 1 plan/backlog text still references `>= 2%` selection and exactly 3 projects. Current decision and generated summary use `>= 1%` and 5 projects.
- Sprint 2 feature pipeline is not implemented yet: `scripts/data_pipeline.py` is still a placeholder.
