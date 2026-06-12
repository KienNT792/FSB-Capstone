# RTPTorrent Project Summary

Updated: 2026-06-12  
Dataset root: `data/repos/rtp-torrent`  
Local Git clone root: `data/git-repos`  
Selection script: `data/scripts/select_rtp_projects.py`  
Loader script: `data/scripts/load_rtp_dataset.py`  
Timestamp script: `scripts/add_timestamps.py`  
DuckDB artifact: `data/test_history.db`

## Selection Criteria

- Failure rate threshold: `>= 1%`
- Minimum mapped TravisCI builds: `>= 100`
- Required patch file: `<project>-patches.csv`
- Selected project limit: `5`

> The `Failure Rate` column below is computed from the RTPTorrent source CSV scan. It can differ from the loaded DuckDB failure rate because the loader writes unique `(repo, job_id, test_id)` rows.

## Project Selection Scan

| Project | Builds | Tests | Failure Rate | Status |
|---------|--------|-------|--------------|--------|
| adamfisk@LittleProxy | 431 | 15,799 | 1.61% | SELECTED |
| apache@sling | 1,403 | 1,555,645 | 0.73% | NOT SELECTED (failure rate < 1%) |
| brettwooldridge@HikariCP | 1,577 | 46,995 | 0.48% | NOT SELECTED (failure rate < 1%) |
| CloudifySource@cloudify | 4,973 | 295,141 | 0.15% | NOT SELECTED (failure rate < 1%) |
| deeplearning4j@deeplearning4j | 982 | 15,511 | 3.78% | SELECTED |
| doanduyhai@Achilles | 773 | 177,366 | 0.40% | NOT SELECTED (failure rate < 1%) |
| DSpace@DSpace | 1,929 | 210,091 | 0.34% | NOT SELECTED (failure rate < 1%) |
| dynjs@dynjs | 935 | 74,741 | 0.62% | NOT SELECTED (failure rate < 1%) |
| eclipse@jetty.project | 381 | 64,113 | 0.22% | NOT SELECTED (failure rate < 1%) |
| facebook@buck | 855 | 783,990 | 0.09% | NOT SELECTED (failure rate < 1%) |
| Graylog2@graylog2-server | 8,384 | 1,373,749 | 0.01% | NOT SELECTED (failure rate < 1%) |
| jcabi@jcabi-github | 2,310 | 555,139 | 0.09% | NOT SELECTED (failure rate < 1%) |
| jOOQ@jOOQ | 3,166 | 83,374 | 0.09% | NOT SELECTED (failure rate < 1%) |
| jsprit@jsprit | 1,061 | 94,253 | 0.11% | NOT SELECTED (failure rate < 1%) |
| julianhyde@optiq | 1,306 | 79,843 | 0.05% | NOT SELECTED (failure rate < 1%) |
| l0rdn1kk0n@wicket-bootstrap | 907 | 51,169 | 20.47% | SELECTED |
| neuland@jade4j | 931 | 35,887 | 2.91% | SELECTED |
| SonarSource@sonarqube | 20,986 | 17,134,773 | 0.03% | NOT SELECTED (failure rate < 1%) |
| square@okhttp | 5,497 | 414,963 | 0.14% | NOT SELECTED (failure rate < 1%) |
| thinkaurelius@titan | 941 | 49,998 | 1.25% | SELECTED |

## Loaded DuckDB Validation

| Project | Loaded test_runs | Fail Rows | Loaded Fail Rate | Null commit_sha | Null commit_sha % | Null duration_ms | Null job_sequence | Timestamped Rows | Timestamp Row Coverage | file_changes |
|---------|-----------------:|----------:|-----------------:|----------------:|------------------:|-----------------:|------------------:|-----------------:|-----------------------:|-------------:|
| adamfisk@LittleProxy | 15,772 | 187 | 1.19% | 4,798 | 30.42% | 0 | 0 | 10,974 | 69.58% | 2,614 |
| deeplearning4j@deeplearning4j | 15,509 | 932 | 6.01% | 884 | 5.70% | 0 | 0 | 14,625 | 94.30% | 61,402 |
| l0rdn1kk0n@wicket-bootstrap | 48,228 | 10,860 | 22.52% | 9,323 | 19.33% | 0 | 0 | 38,905 | 80.67% | 10,248 |
| neuland@jade4j | 35,887 | 1,323 | 3.69% | 36 | 0.10% | 0 | 0 | 35,851 | 99.90% | 3,135 |
| thinkaurelius@titan | 45,058 | 660 | 1.46% | 5,815 | 12.91% | 0 | 0 | 39,243 | 87.09% | 6,413 |

Totals:

- `test_runs`: 160,454
- `file_changes`: 83,812
- `FAIL` rows: 13,962
- `duration_ms IS NULL`: 0
- `job_sequence IS NULL`: 0
- `commit_sha IS NULL`: 20,856
- `timestamp IS NOT NULL`: 139,598
- Overall timestamp row coverage: 87.00%
- Timestamp coverage for rows with `commit_sha`: 100.00%
- Distinct non-null SHAs: 2,652
- Timestamped distinct SHAs: 2,652

## Timestamp Population Status

Timestamp population was performed after cloning the selected GitHub repositories under `data/git-repos/<owner>@<repo>`. The timestamp value is a Unix epoch integer derived from commit metadata. Rows with `commit_sha IS NULL` remain untimestamped and should use `job_sequence` as fallback ordering.

| Project | Resolved SHAs | Eligible Rows | Timestamped Rows | First Commit Date | Last Commit Date | Status |
|---------|--------------:|--------------:|-----------------:|-------------------|------------------|--------|
| adamfisk@LittleProxy | 262 / 262 | 10,974 | 10,974 | 2012-03-16 | 2016-08-07 | PASS |
| deeplearning4j@deeplearning4j | 871 / 871 | 14,625 | 14,625 | 2014-02-15 | 2016-02-13 | PASS |
| l0rdn1kk0n@wicket-bootstrap | 823 / 823 | 38,905 | 38,905 | 2013-03-31 | 2016-08-28 | PASS |
| neuland@jade4j | 314 / 314 | 35,851 | 35,851 | 2012-04-17 | 2016-07-04 | PASS |
| thinkaurelius@titan | 382 / 382 | 39,243 | 39,243 | 2012-06-07 | 2014-07-07 | PASS |

## Sprint 2 Handoff Notes

- The Sprint 2 timestamp gate is passed for all 5 selected projects.
- `scripts/data_pipeline.py` is still a placeholder and must be implemented before feature artifacts can be generated.
- Feature extraction should read labels and history from `data/test_history.db`.
- Generated feature Parquet outputs should be written under `data/features/`.
- Rows without `commit_sha` are real dataset gaps, not pipeline errors. They must either use `job_sequence` fallback or be filtered deliberately with a documented rationale.
