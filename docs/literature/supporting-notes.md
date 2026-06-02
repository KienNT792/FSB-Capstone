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
