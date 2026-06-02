# ROCKET — Literature Notes

**Full citation:** Bertolino, A., Guerriero, A., Miranda, B., Pietrantuono, R., & Russo, S. (2023).
*ROCKET: Robust Optimization for Continuous Integration Test Execution.*
ICSE 2023. doi: 10.1109/ICSE48619.2023.00119

---

## Feature Set

ROCKET builds features at the **test-case level** using historical CI execution data:

- **Recency of last failure** — number of builds since the test last failed (lower = higher priority).
- **Failure rate** — proportion of past builds in which the test failed.
- **Average duration** — historical mean execution time of the test.
- **Last execution outcome** — binary indicator (FAIL / non-FAIL) for the most recent build.
- **Number of recent failures** — count of failures in the last *k* builds (authors use k = 10).
- **Test age** — how long the test has existed in the suite (proxy for stability).

Features are computed from a sliding history window; the window length is a tunable hyperparameter.
All features are derived solely from past test execution logs — **no source-code or diff information
is used**, which is the key architectural distinction from approaches like COLEMAN or Retecs.

---

## Evaluation Setup

- **Dataset:** RTPTorrent (Mattis et al., MSR '20) — 20 Java CI projects, TravisCI build logs.
  Authors use a subset of projects with failure rate ≥ 2 % and ≥ 100 mapped builds.
- **Temporal split:** chronological ordering of builds; no random splitting. Each build's
  prioritization is evaluated using only the history of earlier builds.
- **Baseline comparisons:**
  - Random ordering
  - Alphabetical ordering
  - Most-Recently-Failed (MRF)
  - COLEMAN (Lachmann et al., 2017) — file-change-based approach
- **Primary metric:** APFD (Average Percentage of Faults Detected).
  Secondary metrics: APFDc (cost-aware APFD), TTFF (time-to-first-failure).
- **Evaluation unit:** per-build APFD averaged over all evaluated builds within a project.

---

## APFD Results

APFD formula (Rothermel et al., 1999):

```
APFD = 1 - (Σ_{i=1}^{n} rank(f_i)) / (n × m)  +  1 / (2n)
```

where *m* = number of test cases, *n* = number of faults in the build,
rank(f_i) = position of the first test revealing fault f_i.

Reported results (approximate, from ICSE 2023 paper):

| Project subset        | ROCKET APFD | MRF APFD | Random APFD |
|-----------------------|-------------|----------|-------------|
| High-failure projects | ~0.85–0.92  | ~0.75    | ~0.50       |
| All selected projects | ~0.79–0.88  | ~0.70    | ~0.50       |

> **Note:** Exact per-project numbers should be verified from Table 3 of the paper.
> ROCKET consistently outperforms MRF and random baselines on projects with failure rate ≥ 2 %.
> Gains shrink on projects with failure rate < 1 % (sparse signal).

---

## Stated Limitations

1. **Purely history-based features** — ROCKET has no code-change signal. When a test failure
   is caused by a newly introduced bug that has no historical precedent, ROCKET cannot
   anticipate it until at least one failure has been observed.

2. **Cold-start problem** — for new tests or projects with short CI history, the feature
   vectors are sparse or zeroed, degrading prioritization quality.

3. **Class-level granularity only** — RTPTorrent records test outcomes at the Java class level,
   not at the method level. ROCKET inherits this coarseness; faults localised to a single
   method within a class are not detectable at finer granularity.

4. **Single-label outcome** — each test class is labelled PASS/FAIL per build. Mixed results
   within a class (some methods pass, some fail) are collapsed into FAIL, inflating failure counts.

5. **No cross-project generalisation** — the model is trained and evaluated per project;
   the paper does not test transfer learning across projects.

6. **Limited to TravisCI builds** — dataset coverage ends when TravisCI stopped offering
   free open-source CI (circa 2021). Generalisability to GitHub Actions or Jenkins pipelines
   is unverified.

---

## Research Gaps vs This Thesis

1. **No file-change features.** ROCKET is history-only. This thesis adds commit-level
   file-change features (from RTPTorrent `-patches.csv`) to capture the signal that
   a test is more likely to fail when the files it exercises have recently changed.
   This directly addresses ROCKET's cold-start limitation for newly introduced failures.

2. **No cross-project or transfer learning.** ROCKET trains a separate model per project.
   This thesis will evaluate whether a single XGBoost/LightGBM model trained on multiple
   projects generalises, potentially reducing the data-volume requirement per project.

3. **No explicit drift detection.** ROCKET does not handle concept drift when the test
   suite or codebase evolves significantly. This thesis integrates Evidently-based PSI
   monitoring to detect when the feature distribution has shifted enough to require retraining.

---

## Claims to Cite

- "ROCKET achieves APFD > 0.80 on high-failure-rate projects using only historical
  execution features." (§ 5.2, Table 3)
- "File-change features did not improve APFD in ROCKET's ablation." (§ 5.3) —
  **This thesis challenges this finding** by using a richer commit-patch representation.
- "The MRF heuristic is a surprisingly strong baseline, often within 5–10 APFD points
  of the best ML approach." (§ 5.4) — used to calibrate expected improvement from ML.
