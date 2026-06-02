# Design Decisions Log

Last updated: 2026-06-02

This file is the compact project-memory version of design decisions. The longer Sprint 1 record is in `docs/decisions-log.md`.

## Decided

| Date | Decision | Rationale | Consequences |
|------|----------|-----------|--------------|
| 2026-05-01 | Use RTPTorrent as the primary dataset instead of replaying `mvn test`. | Apache Commons replay produced environment-noise labels from JDK/plugin/network failures. RTPTorrent is published, reproducible CI history. | Pipelines read CSV/SQLite ground truth. Git clones, if added later, are metadata sources only. |
| 2026-05-10 | Lower project selection threshold from `>= 2%` to `>= 1%` and evaluate 5 projects. | Only 3 projects qualified at `>= 2%`, which was too narrow for the thesis diversity claim. | Selected projects are wicket-bootstrap, jade4j, deeplearning4j, LittleProxy, and titan. Report low-failure projects with caveats. |
| 2026-05-20 | Populate `timestamp` in Phase 2; use `job_sequence` as Sprint 1 temporal fallback. | `tr_all_built_commits.csv` does not include timestamps; resolving commit dates requires cloned repos. | Sprint 1 loader stores `timestamp = NULL`. Temporal splitting must fall back to per-project `job_sequence` until timestamp enrichment is done. |

## Working Rules From Decisions

- Do not reintroduce Maven replay as a data-labeling step.
- Do not move RTPTorrent source CSVs out of `data/repos/rtp-torrent/`.
- Feature extraction should read from SQLite tables loaded from RTPTorrent.
- Commit/file-change features should use RTPTorrent `-patches.csv` data via `file_changes`.
- Cross-validation and temporal splits must be per-project and time/order aware.
- Any result on LittleProxy or titan needs an explicit low-failure-rate/high-variance caveat.

## Known Drift To Resolve

- Some Sprint 1 plan/backlog text still references `>= 2%` selection and exactly 3 projects. Current decision and generated summary use `>= 1%` and 5 projects.
- `data/scripts/load_rtp_dataset.py` currently identifies auto-selected projects by checking whether a summary line contains `"SELECTED"`. Because `"NOT SELECTED"` also contains that substring, verify/fix this before treating an auto-loaded DB as selected-project-only.
