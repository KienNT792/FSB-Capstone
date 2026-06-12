# Design Decisions Log

Last updated: 2026-06-12

This file is the compact project-memory version of design decisions. The longer Sprint 1 record is in `docs/decisions-log.md`.

## Decided

| Date | Decision | Rationale | Consequences |
|------|----------|-----------|--------------|
| 2026-05-01 | Use RTPTorrent as the primary dataset instead of replaying `mvn test`. | Apache Commons replay produced environment-noise labels from JDK/plugin/network failures. RTPTorrent is published, reproducible CI history. | Pipelines read CSV/DuckDB ground truth. Git clones are metadata sources only. |
| 2026-05-10 | Lower project selection threshold from `>= 2%` to `>= 1%` and evaluate 5 projects. | Only 3 projects qualified at `>= 2%`, which was too narrow for the thesis diversity claim. | Selected projects are wicket-bootstrap, jade4j, deeplearning4j, LittleProxy, and titan. Report low-failure projects with caveats. |
| 2026-05-20 | Load `timestamp = NULL` first, then enrich from cloned Git repos. | `tr_all_built_commits.csv` does not include timestamps; resolving commit dates requires cloned repos. | Sprint 1 loader remains reproducible from CSVs; timestamp enrichment is a separate step. Rows without `commit_sha` use `job_sequence` fallback. |
| 2026-06-12 | Resolve timestamps with batched Git CLI calls instead of GitPython per-SHA lookup. | GitPython per-SHA lookup was too slow for large repos; blobless clones can contain unreachable commit objects. | `scripts/add_timestamps.py` uses `git log --all` plus batched `git show` fallback. All 2,652 non-null SHAs across 5 selected projects are timestamped. |

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
