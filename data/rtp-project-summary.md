# RTPTorrent Project Summary

Updated: 2026-06-12  
Dataset root: `data/repos/rtp-torrent`  
Selection script: `data/scripts/select_rtp_projects.py`  
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
| adamfisk@LittleProxy | 431 | 15799 | 1.61% | SELECTED |
| apache@sling | 1403 | 1555645 | 0.73% | NOT SELECTED (failure rate < 1%) |
| brettwooldridge@HikariCP | 1577 | 46995 | 0.48% | NOT SELECTED (failure rate < 1%) |
| CloudifySource@cloudify | 4973 | 295141 | 0.15% | NOT SELECTED (failure rate < 1%) |
| deeplearning4j@deeplearning4j | 982 | 15511 | 3.78% | SELECTED |
| doanduyhai@Achilles | 773 | 177366 | 0.40% | NOT SELECTED (failure rate < 1%) |
| DSpace@DSpace | 1929 | 210091 | 0.34% | NOT SELECTED (failure rate < 1%) |
| dynjs@dynjs | 935 | 74741 | 0.62% | NOT SELECTED (failure rate < 1%) |
| eclipse@jetty.project | 381 | 64113 | 0.22% | NOT SELECTED (failure rate < 1%) |
| facebook@buck | 855 | 783990 | 0.09% | NOT SELECTED (failure rate < 1%) |
| Graylog2@graylog2-server | 8384 | 1373749 | 0.01% | NOT SELECTED (failure rate < 1%) |
| jcabi@jcabi-github | 2310 | 555139 | 0.09% | NOT SELECTED (failure rate < 1%) |
| jOOQ@jOOQ | 3166 | 83374 | 0.09% | NOT SELECTED (failure rate < 1%) |
| jsprit@jsprit | 1061 | 94253 | 0.11% | NOT SELECTED (failure rate < 1%) |
| julianhyde@optiq | 1306 | 79843 | 0.05% | NOT SELECTED (failure rate < 1%) |
| l0rdn1kk0n@wicket-bootstrap | 907 | 51169 | 20.47% | SELECTED |
| neuland@jade4j | 931 | 35887 | 2.91% | SELECTED |
| SonarSource@sonarqube | 20986 | 17134773 | 0.03% | NOT SELECTED (failure rate < 1%) |
| square@okhttp | 5497 | 414963 | 0.14% | NOT SELECTED (failure rate < 1%) |
| thinkaurelius@titan | 941 | 49998 | 1.25% | SELECTED |

## Loaded DuckDB Validation

| Project | Loaded test_runs | Fail Rows | Loaded Fail Rate | Null commit_sha | Null commit_sha % | Null duration_ms | Null job_sequence | Timestamped Rows | file_changes |
|---------|-----------------:|----------:|-----------------:|----------------:|------------------:|-----------------:|------------------:|-----------------:|-------------:|
| adamfisk@LittleProxy | 15,772 | 187 | 1.19% | 4,798 | 30.42% | 0 | 0 | 0 | 2,614 |
| deeplearning4j@deeplearning4j | 15,509 | 932 | 6.01% | 884 | 5.70% | 0 | 0 | 0 | 61,402 |
| l0rdn1kk0n@wicket-bootstrap | 48,228 | 10,860 | 22.52% | 9,323 | 19.33% | 0 | 0 | 0 | 10,248 |
| neuland@jade4j | 35,887 | 1,323 | 3.69% | 36 | 0.10% | 0 | 0 | 0 | 3,135 |
| thinkaurelius@titan | 45,058 | 660 | 1.46% | 5,815 | 12.91% | 0 | 0 | 0 | 6,413 |

Totals:

- `test_runs`: 160,454
- `file_changes`: 83,812
- `duration_ms IS NULL`: 0
- `job_sequence IS NULL`: 0
- `timestamp IS NOT NULL`: 0

## Timestamp Dry-Run Status

Timestamp population was not performed. Dry-run coverage is currently `0.0%` for all selected projects because the required local Git clones are missing under `data/git-repos`.

| Project | Resolvable SHAs | Eligible Rows | Missing Repo SHAs | Status |
|---------|----------------:|--------------:|------------------:|--------|
| adamfisk@LittleProxy | 0 / 262 | 0 / 10,974 | 262 | DEFERRED |
| deeplearning4j@deeplearning4j | 0 / 871 | 0 / 14,625 | 871 | DEFERRED |
| l0rdn1kk0n@wicket-bootstrap | 0 / 823 | 0 / 38,905 | 823 | DEFERRED |
| neuland@jade4j | 0 / 314 | 0 / 35,851 | 314 | DEFERRED |
| thinkaurelius@titan | 0 / 382 | 0 / 39,243 | 382 | DEFERRED |
