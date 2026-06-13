# Supporting Literature Notes

---

## RTPTorrent — Mattis et al., MSR 2020

**Citation:** `@rtptorrent` in `references.bib`

### Dataset Structure

RTPTorrent provides pre-collected TravisCI CI build data for **20 open-source Java projects**,
drawn from GitHub repositories that used TravisCI as their CI platform.

Each project directory (`<owner>@<repo>/`) contains:

| File | Contents |
|------|----------|
| `<project>.csv` | One row per (job, test-class) pair: `travisJobId`, `testName`, `duration`, `count`, `failures`, `errors`, `skipped` |
| `<project>-patches.csv` | File-level changes per commit: `sha`, `name` (file path) |
| `<project>-pr.csv` | Pull-request metadata |
| `<project>-offenders.csv` | Jobs identified as failure-introducing |
| `baseline/` | Baseline evaluation results (APFD for random/alphabetical ordering) |

The root file `tr_all_built_commits.csv` maps TravisCI job IDs (`tr_job_id`) to git commit SHAs,
enabling linkage between test outcomes and source-code changes.

### Collection Methodology

- Build logs were retrieved from the TravisCI public API.
- Test outcome data were parsed from JUnit XML reports embedded in the build logs.
- Granularity is **Java class level** — one row per test class per build job.
  Method-level outcomes are not available.
- Coverage period: approximately 2013–2020 (varies by project).

### Known Limitations

1. **Class-level only.** No method-level test outcomes; fault localisation is coarse.
2. **SHA mapping gaps.** Many Travis job IDs have no corresponding git SHA in
   `tr_all_built_commits.csv` (null rate varies 0–83 % across projects). Rows without
   a SHA cannot be linked to file-change features from `-patches.csv`.
3. **Imbalanced failure rates.** Most projects have failure rate < 2 %; only 3 of 20
   qualify under the threshold used in this thesis. This limits the training set.
4. **Archived repos.** Several projects (e.g., `deeplearning4j`) have since changed
   their CI system or moved repositories, making fresh data collection impossible.
5. **TravisCI-only.** The dataset does not cover GitHub Actions, Jenkins, or other CI
   systems; generalisability is uncertain.

### How Elsner 2021 Used This Dataset

Elsner et al. (2021) used RTPTorrent as the evaluation benchmark for their
file-change-based regression test prioritization approach. They selected projects with
sufficient failure signal (≥ 2 % failure rate) and evaluated APFD using a chronological
train/test split. Their work demonstrates that file-change features (from `-patches.csv`)
provide meaningful additional signal beyond history-only approaches.
This thesis follows a similar feature-engineering strategy but extends it with
gradient-boosted tree models and explicit drift detection.

---

---

## Coverage Metrics — SHA Coverage vs Row Coverage

Two distinct coverage metrics are used throughout the Sprint 1 and Sprint 2 reports. They measure different things and should not be conflated.

### SHA Coverage

**Definition:** The fraction of *distinct non-null commit SHAs* in the `test_runs` table that were successfully resolved to a Unix timestamp via `git log` or `git show` from the cloned repository.

```
SHA Coverage = resolved_distinct_SHAs / total_distinct_non_null_SHAs
```

This metric answers: "For every unique commit we know about, did we find its timestamp?" A value of 100% means every commit identity in the dataset has a known wall-clock time.

### Row Coverage

**Definition:** The fraction of *rows* in `test_runs` that have a non-NULL `timestamp` value after the timestamp enrichment pass.

```
Row Coverage = rows_with_timestamp / total_rows
```

This metric answers: "What percentage of test execution records have a resolved timestamp?" Row coverage is always ≤ SHA coverage at the project level because some rows have `commit_sha IS NULL` (a source-data gap in RTPTorrent) and can never receive a timestamp regardless of SHA resolution quality.

### Why the two metrics diverge

For `adamfisk@LittleProxy`, SHA coverage = 100% but row coverage = 69.58%. The gap (30.42%) is entirely explained by rows where `commit_sha IS NULL` in the source CSV — Travis CI did not record a git SHA for those builds. This is not a timestamp-resolution failure; it is a structural gap in the upstream data. Rows in this gap use `job_sequence` as their ordering proxy (tracked by `feature_source = 'job_sequence'`).

### Thesis usage

- Report SHA coverage to characterise data completeness from a commit-identity perspective.
- Report row coverage to characterise how much of the training data has a reliable temporal anchor.
- When discussing class imbalance or temporal split quality, use row coverage as the relevant denominator.

---

## Failure Rate — Source CSV vs Loaded DuckDB

Two failure rate values appear in the project documentation for `l0rdn1kk0n@wicket-bootstrap` (and to a lesser extent other projects). They are both correct but measure different populations.

| Source | Value | What it counts |
|---|---|---|
| RTPTorrent scan (`select_rtp_projects.py`) | 20.47% | Failure rows in the raw source CSV before deduplication |
| Loaded DuckDB (`test_runs` table) | 22.52% | Failure rows after loading unique `(repo, job_id, test_id)` records |

The loader writes one row per unique `(repo, job_id, test_id)` triple. If the source CSV has duplicate rows (e.g., a test class reported twice in one build log), the loader deduplicates them. This can shift the failure rate if duplicated rows are non-uniformly distributed across passing and failing outcomes. For wicket-bootstrap, deduplication removed more passing rows than failing rows, raising the observed failure rate from 20.47% to 22.52%.

**Thesis usage:** Use the DuckDB value (22.52%) when reporting results, as this is the population the model trains and evaluates on. Use the source-CSV value (20.47%) only when describing the project selection scan or when comparing against other papers that cite the raw RTPTorrent statistics.

---

## Bertolino et al. — 2020 (Empirical Study of RTP Techniques)

**Candidate citation key:** `bertolino2020`

### Summary

An empirical comparison of regression test prioritization techniques across multiple
open-source projects. The paper evaluates history-based, coverage-based, and hybrid
approaches using APFD as the primary metric.

### Key Findings

- History-based methods (using past failure records) consistently outperform
  coverage-based methods when historical data is available.
- The APFD gain from ML over simple heuristics (MRF) depends heavily on the
  failure rate of the project; low-failure-rate projects show minimal improvement.
- Cross-project evaluation (training on one project, testing on another) shows
  significant degradation, suggesting project-specific models are necessary
  unless a strong domain adaptation mechanism is used.

### APFD Formula (from Rothermel et al., 1999, as cited in Bertolino 2020)

```
APFD = 1 - (Σ_{i=1}^{n} rank(f_i)) / (n × m)  +  1 / (2n)
```

- *m*: number of test cases in the suite
- *n*: number of faults (failing tests) in the evaluated build
- rank(f_i): position in the prioritized order of the first test that reveals fault *f_i*
- APFD ∈ (0, 1]; higher is better; random ordering ≈ 0.5

Cited from: Rothermel, G., Untch, R. H., Chu, C., & Harrold, M. J. (1999).
*Prioritizing Test Cases for Regression Testing.* IEEE TSE, 25(5), 929–948.

---

## Elsner et al. — 2021 (File-Change-Based RTP)

**Candidate citation key:** `elsner2021`

### Summary

Elsner et al. propose a test prioritization approach that uses file-change features
extracted from version control history. For each test, they compute which source files
the test has historically been correlated with (co-failure signal), and then prioritize
tests based on how many of those files were changed in the current commit.

### Key Findings

- File-change features outperform pure history-based features on projects where
  the relationship between code changes and test failures is stable.
- The approach degrades when SHA mapping is incomplete (high null-SHA rate),
  since file-change features cannot be computed for unmapped builds.
- APFD improvements over MRF baseline: ~5–15 percentage points on qualifying projects.

### Relevance to This Thesis

Elsner 2021 demonstrates that `-patches.csv` from RTPTorrent provides useful
file-change signal. This thesis combines both history-based features (as in ROCKET)
and file-change features (as in Elsner 2021) in a single gradient-boosted tree model,
aiming to capture complementary signal from both sources.

---

## Additional Source — Rothermel et al. 1999 (APFD Definition)

The original paper introducing APFD as a metric for test prioritization evaluation.
Canonical reference for the APFD formula and its interpretation.

**Citation key:** `rothermel1999`

---

## Sprint 2 EDA Summary (2026-06-12)

### Dataset Overview

The combined feature corpus produced by Sprint 2 consists of **160,454 rows × 37 columns** across 5 selected RTPTorrent projects. After excluding the non-feature audit columns (`commit_sha`, `test_id`, `label`, `timestamp`, `feature_source`, `repo`), there are **31 numeric feature columns** available for model training. The overall failure rate across the combined corpus is **8.70%** (13,962 FAIL rows out of 160,454 total), with substantial variation across projects ranging from 1.19% (`adamfisk@LittleProxy`) to 22.52% (`l0rdn1kk0n@wicket-bootstrap`).

### Top-5 Features by Mutual Information

Computed via `sklearn.feature_selection.mutual_info_classif` on the combined corpus with `random_state=42` and missing values filled with 0.

| Rank | Feature | MI Score |
|---|---|---|
| 1 | `days_since_last_fail` | 0.2365 |
| 2 | `failure_rate_90d` | 0.2002 |
| 3 | `failure_rate_30d` | 0.1888 |
| 4 | `consecutive_passes` | 0.1622 |
| 5 | `failure_rate_7d` | 0.1558 |

### EDA Conclusions

All top-5 features by mutual information are test-history features (recent and rolling per-test failure history), consistent with regression test prioritization literature. Correlation-with-label ranking (`last_outcome`, `failure_rate_90d`, `failure_rate_30d`, `failure_rate_7d`, `consecutive_passes`) corroborates this from a linear perspective. No commit-metadata or dependency-based feature appears in the top-5, consistent with elevated `commit_meta_missing` rates limiting their coverage for several projects. The scatter plot of `days_since_last_fail` vs `failure_rate_30d` confirms a clear cluster: failing tests tend to have short recency (days_since_last_fail < 30) and high 30-day failure rate, while passing tests are spread broadly.

No data leakage was detected — all history features are computed from records strictly before `as_of_ts`; rows without `commit_sha` use `job_sequence` fallback (tracked via `feature_source` column, excluded from model inputs per Decision 5).

### Per-Project Missing Rate Summary

| Project | Shape | Failure rate | commit_meta_missing | commit_diff_missing |
|---------|-------|--------------|----------------------|----------------------|
| `adamfisk@LittleProxy` | (15772, 37) | 1.19% | 30.42% | 30.42% |
| `deeplearning4j@deeplearning4j` | (15509, 37) | 6.01% | 5.70% | 100.00% |
| `l0rdn1kk0n@wicket-bootstrap` | (48228, 37) | 22.52% | 19.53% | 19.53% |
| `neuland@jade4j` | (35887, 37) | 3.69% | 0.10% | 0.10% |
| `thinkaurelius@titan` | (45058, 37) | 1.46% | 12.91% | 12.91% |
| **Combined** | **(160454, 37)** | **8.70%** | — | — |

`commit_meta_missing` equals the null-`commit_sha` fraction for each project and is the rate at which the `job_sequence` fallback was used for temporal ordering. `commit_diff_missing` tracks whether line-count diff features could be computed from local git objects; `deeplearning4j` shows 100% because the local clone is blobless. See `docs/decisions-log.md` Pending table (2026-06-12) for resolution plan.
