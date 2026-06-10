# Paper Analysis

## Metadata

| Field              | Value |
| ------------------ | ----- |
| Title              | RTPTorrent: An Open-source Dataset for Evaluating Regression Test Prioritization |
| Authors            | Toni Mattis, Patrick Rein, Falco Dürsch, Robert Hirschfeld |
| Year               | 2020 |
| Conference/Journal | MSR '20 — 17th International Conference on Mining Software Repositories |
| DOI                | https://doi.org/10.1145/3379597.3387458 |
| Link               | https://doi.org/10.1145/3379597.3387458 |
| Pages              | 12 pages (pp. 385–396) |
| Keywords           | Regression Test Prioritization, TravisCI, GitHub, Java, Dataset |

---

# 1. Executive Summary

## One-Sentence Summary

> This paper introduces RTPTorrent, a publicly archived dataset of 20 open-source Java projects with over 100,000 real-world CI build jobs from TravisCI (2007–2016), constructed to address the ecological validity gap in existing RTP evaluation datasets that rely predominantly on synthetic faults and small, non-representative programs.

## TL;DR

- **Problem:** RTP evaluation datasets predominantly use synthetic/seeded faults, manually created tests, and small programs (e.g., Siemens programs under 1,000 LOC) that do not resemble real-world software; only 19% of datasets in the literature are properly archived.
- **Research Gap:** No large, open, reproducible dataset exists that combines fine-grained CI build histories with real failure data and full VCS commit histories from actively developed, representative real-world Java projects.
- **Proposed Solution:** RTPTorrent — 20 Java projects from GitHub/TravisCI with full Git histories, test-level build results, and links to GHTorrent and TravisTorrent, enabling history-based, code-based, and change-based RTP evaluation.
- **Main Result:** Demonstrated fault effectiveness heuristic (history-based) raises average APFD from 25.9% (original/unordered) to 81.1% (prioritized) across the dataset, validating the dataset's usability.
- **Key Contribution:** Dataset + literature survey of 117 RTP papers + non-trivial baseline + quantitative representativeness analysis against all GitHub Java projects.

---

# 2. Research Problem

## Problem Statement

Evaluating RTP techniques requires datasets with programs, test cases, and fault information. Existing datasets fail to represent real-world development activity: they use synthetic programs, manually seeded faults, or small code bases (e.g., Siemens programs ≤1,000 LOC). This threatens ecological validity, as techniques that work on controlled datasets may not transfer to real-world settings.

## Motivation

Fine-grained historical data is now readily available through infrastructure like GHTorrent and TravisTorrent. There is no fundamental reason to continue relying on synthetic datasets when real-world CI build logs and VCS histories can serve as a richer, more ecologically valid data source. Reproducibility is also critically lacking: only 19.0% of datasets surveyed are properly archived.

## Existing Challenges

- **Representativeness:** Mean number of projects per RTP study is 5.25 (SD = 6.36); the Siemens programs (≤1,000 LOC) are used in 21.4% of all studies despite being unrepresentative of modern software.
- **Artificiality of faults:** 57.9% of studies use manually seeded faults; only 38.1% use historic real faults.
- **Archival failure:** Only 19% of datasets are archived; 83.3% of those are archived solely because they reuse unmodified SIR datasets.
- **History resolution:** Most studies that use historic variants do so only at release granularity, not at the commit level; this obscures fine-grained failure behavior.

---

# 3. Research Gap

## Gap Explicitly Identified By Authors

- Most evaluation studies use datasets with few projects (mean 5.25), many synthetic or small programs, and non-historic test cases and faults.
- No publicly archived, large-scale dataset combines fine-grained CI build logs (commit-level), real test failures, test execution timing, and full source code history for multiple diverse, actively developed projects.
- Reuse of datasets in the community is observable (primarily SIR), but breadth is insufficient and representativeness is limited.

## Gap Inferred From The Paper

- The high ecological validity potential of TravisTorrent was known prior to RTPTorrent but had not been exploited at the test-prioritization level specifically; the dataset needed test-level result extraction that was not present in TravisTorrent's raw build logs.
- History-based RTP approaches (which depend on fine-grained CI runs, not releases) were underserved by existing datasets, as even studies claiming historic variants typically used only release snapshots.
- The interaction between confounding factors present in real CI data (manual builds, pull request builds, configuration changes, hardware variability) and RTP technique performance had not been systematically studied.

## Why Existing Methods Fail

| Existing Approach/Dataset | Limitation |
| ------------------------- | ---------- |
| SIR (Siemens programs) | ≤1,000 LOC; not representative of modern software; only release-level variants |
| SIR Java dataset | Small number of projects; manually seeded faults; not at commit granularity |
| Defects4J | High-quality fault database but fixed fault set, not reflecting CI failure distributions over time |
| Google Shared Dataset (GSDTSR) | Not publicly archived; inaccessible to external researchers |
| TravisTorrent (Beller et al. 2017) | Does not contain test-level results (only build-level pass/fail); requires additional parsing |
| Individual industrial study datasets | Inaccessible; results not reproducible by external parties |

---

# 4. Proposed Method

## Simple Explanation

The authors identified 20 mature, actively developed Java projects on GitHub that used TravisCI for CI. They parsed raw TravisCI build logs using regular expressions to extract test-level results (per test class: count, failures, errors, skipped, duration, execution order index). They linked these results to Git commit hashes and TravisTorrent job IDs, published the result as a relational dataset, and demonstrated its use by implementing a well-known history-based prioritization heuristic (demonstrated fault effectiveness) as a non-trivial baseline.

## Technical Explanation

**Project Selection Criteria:**
1. Written in Java (largest ecosystem of analysis tools, frequent in RTP literature).
2. Highest-ranked by number of logged failures (ensures sufficient failure signal for RTP evaluation).
3. Varying size and maturity to represent a broad spectrum of GitHub's Java community.

**Data Procurement:**
- Source: TravisTorrent raw build logs (2007–2016).
- Parser targets: Maven Surefire and Facebook Buck output formats (identified as producing the most complete test-level logs including passing tests).
- Extraction per test class per build job: test name, execution index (original order), total count, failures, errors, skipped, duration (seconds, as logged by JUnit).
- 9.28% of test durations are 0.0s (below Java clock resolution); 17 negative durations from test runner defects.

**Dataset Structure:**
- Relational format: `built_commits.csv` (job_id → commit SHA1) + `<project>.csv` (job_id, test name, index, count, failures, errors, skipped).
- Linked to TravisTorrent via `tr_job_id` (for branch, timestamp, build metadata) and to GHTorrent via SHA1 (for author, PR, issue context).
- Full Git repositories archived (fork-verified where original repos were relocated).

**Baseline — Demonstrated Fault Effectiveness:**
- Priority function: Pₜ(n) = α·Fₜ(n) + (1−α)·Pₜ(n−1), with P(0)=0, α=0.8.
- Fₜ(n) = 1 if test t failed in build n, else 0.
- Only non-concurrent past builds included. α=0.8 weights recent failures heavily.
- Metric: Standard APFD (unweighted, treating each failure as one fault).

## Architecture

```
TravisCI Raw Build Logs (2007–2016)
        ↓
Regular Expression Parsing (Maven Surefire / Buck output)
        ↓
Per-Job, Per-Test Result Extraction
(test name, index, count, failures, errors, skipped, duration)
        ↓
Relational Dataset (built_commits.csv + <project>.csv)
        ↓ (linked via job_id)
TravisTorrent (branch, timestamp, build metadata)
        ↓ (linked via SHA1)
GHTorrent (author, PR, issue context)
        ↓ (linked via project)
Git Repositories (full source code history)
        ↓
RTPTorrent: Unified dataset for history-based + code-based + change-based RTP evaluation
```

## Workflow

1. Select 20 Java GitHub projects by failure count, size/maturity diversity, and TravisCI usage within TravisTorrent time range (2007–2016).
2. Parse raw TravisCI build logs per project using Maven Surefire / Buck regex patterns; extract test-level results per build job.
3. Link test results to Git commit hashes (via `built_commits.csv`) and to TravisTorrent/GHTorrent via `tr_job_id` and SHA1.
4. Archive Git repositories (fork-verified) alongside the relational dataset.
5. Run demonstrated fault effectiveness heuristic on the dataset; report per-project and aggregate APFD as a non-trivial baseline.

## Technologies Used

- **Models/Heuristics:** Demonstrated fault effectiveness (exponential moving average of failure history, α=0.8)
- **Algorithms:** Regular expression parsing of build logs; exponential smoothing for priority scoring; standard APFD computation
- **Dataset sources:** TravisTorrent (raw CI logs), GHTorrent (commit/author metadata), GitHub (Git repositories), Maven Surefire and Facebook Buck output formats
- **Frameworks:** Git VCS, TravisCI, Maven, JUnit (duration logging)
- **Tools:** dblp (literature survey retrieval), SALSA literature review process

---

# 5. Experimental Setup

## Dataset

| Dataset Component | Size | Purpose |
| ----------------- | ---- | ------- |
| 20 Java open-source GitHub projects | 10,288–673,484 lines; 69–5,486 classes | Corpus for RTP evaluation |
| Build jobs | 383–53,307 per project; >100,000 total | Unit of evaluation (CI run) |
| Commits | 205–13,763 per project; union 62,133 available in repos | Version history linkage |
| Time range | 2007–2016 (up to 9 years per project) | Long-term evolution coverage |
| Test cases (TC) per build | Avg. 14.94 (deeplearning4j) – 682.92 (buck) | Test suite size diversity |
| Test methods (TM) per build | Avg. 30.82 – 4,052.42 | Method-level granularity |
| Failing TM per build | Avg. 0.1 (graylog2) – 32.74 (wicket-bootstrap) | Failure rate diversity |

## Evaluation Metrics

- **APFD (Average Percentage of Faults Detected):** Primary metric. Range [0,1]; higher = earlier fault detection. One-to-one failure-to-fault mapping applied (standard practice when faults are not synthesized). Formula: APFD(S,F) = 1 − (Σ_f TF(f)) / (|S|×|F|) + 1/(2|S|).
- Note: APFDc (cost-aware) is referenced in the broader literature but not used for the baseline in this paper.

## Baseline Methods

1. **Original build order (unmodified):** Tests run in their recorded execution index order — reflects default test runner ordering. Avg. APFD: 25.9%.
2. **Demonstrated fault effectiveness (prioritized):** Exponential moving average of failure history (α=0.8). Avg. APFD: 81.1%. Serves as the non-trivial baseline.
- Note: Random ordering baseline is mentioned in the literature context but not separately computed in this paper's micro-study.

---

# 6. Results

## Quantitative Results

| Method | Metric | Result |
| ------ | ------ | ------ |
| Original build order (all projects) | Avg. APFD | 25.9% |
| Demonstrated fault effectiveness (all projects) | Avg. APFD | 81.1% |
| Best individual project (buck) | Prioritized APFD | 96.5% |
| Worst individual project (Achilles) | Prioritized APFD | 53.0% |
| Largest improvement (cloudify) | Original → Prioritized APFD | 17.7% → 91.2% |
| Smallest improvement (dynjs) | Original → Prioritized APFD | 45.7% → 58.2% |
| Dataset representativeness | Avg. commits per project | 11,324 (vs. 141 for all GitHub Java projects) |
| Dataset representativeness | Avg. authors per project | 128 (vs. 5 for all GitHub Java projects) |

## Key Findings

- A simple exponential moving average of failure history (no code or change data) achieves 81.1% average APFD across 20 diverse projects — a 3.13× improvement over the unmodified test order.
- The RTPTorrent dataset spans a wide range of project sizes, maturity levels, and failure rates, making it suitable as a heterogeneous evaluation corpus.
- The dataset is biased toward larger, more active projects (intentionally), as RTP is of little benefit in small or immature projects.
- Fine-grained CI data (commit-level, not release-level) reveals behavioral nuances — streaks of repeatedly failing tests, effects of configuration changes, pull request builds — that are absent from synthetic datasets.
- 9 out of 20 projects achieve prioritized APFD > 80%, confirming the predictive value of recent failure history even without any code or change analysis.

## Authors' Claims

- RTPTorrent is the first large-scale, openly archived dataset combining fine-grained CI build logs, test-level results, and full VCS history for diverse real-world Java projects specifically designed for RTP evaluation.
- The demonstrated fault effectiveness heuristic achieves competitive performance, validating the dataset's utility and the predictive power of fine-grained build history.
- The literature survey shows that only 19% of existing datasets are properly archived, and most rely on non-representative programs or synthetic faults.
- RTPTorrent improves ecological validity, reproducibility, and long-term availability for RTP research.

---

# 7. Strengths

1. **Fills a genuine dataset gap:** First large-scale, properly archived, openly available RTP dataset with fine-grained (commit-level, not release-level) real CI failures from actively developed real-world projects.
2. **Ecosystem compatibility:** Linked to TravisTorrent and GHTorrent, enabling researchers to enrich the dataset with additional metadata (branch, author, PR context, timestamps) without data redundancy.
3. **Literature survey foundation:** The 117-paper systematic survey provides rigorous evidence that the dataset gap is real, not just asserted — dataset design choices are directly motivated by documented field-wide deficiencies.
4. **Representative diversity:** Projects span 10K–673K LOC, 63–53,307 builds, and up to 9 years of history, covering a wide spectrum of Java project maturity.
5. **Immediate usability:** Non-trivial baseline included; failure signal strong enough that even the simplest history-based heuristic achieves 81.1% APFD, confirming the dataset contains meaningful failure patterns.

---

# 8. Weaknesses

1. **No APFDc (cost-aware) baseline:** The micro-study uses unweighted APFD, ignoring test execution duration — a known limitation since different tests have vastly different costs (TC Time ranges from 0.1s for jade4j to 68.5s for titan). APFDc would be more appropriate for real cost-effectiveness evaluation.
2. **Java-only scope:** Restricting to Java excludes multi-language projects and limits generalizability; the authors acknowledge extension to other ecosystems as future work.
3. **No flaky test handling:** CI builds contain inherent noise from flaky tests, configuration changes, hardware variability, and concurrent builds — none of which are filtered or labeled in the dataset.
4. **Time range limited to TravisTorrent coverage (2007–2016):** Data predates modern CI practices (e.g., GitHub Actions); findings may not transfer to current CI environments.
5. **No method-level test granularity:** Test results are at test class granularity (not test method), because TravisCI does not log method-level results. This limits precision for fine-grained prioritization studies.
6. **Micro-study is illustrative only:** The baseline comparison involves only one heuristic against the unmodified order; no comparison against random ordering, other established baselines, or ML-based techniques is provided.

---

# 9. Threats To Validity

## Internal Validity

- Regex parsing of build logs may mis-attribute test results in the presence of parallelized test execution (multiple tests announced before any results are logged); a best-effort pairing heuristic is applied but errors are possible.
- Negative durations (17 cases) and zero durations (9.28% of test cases) indicate test runner defects and clock resolution limits; these affect timing-based analysis.
- Not all commits are available in Git repositories (41 commits missing due to rejected pull requests); minor impact on VCS-linked analyses.

## External Validity

- Dataset is biased toward larger, more active Java projects — results may not transfer to smaller, less mature, or non-Java projects.
- TravisTorrent's time range (2007–2016) means the dataset predates modern CI tooling (GitHub Actions, containerized builds); failure patterns and build structures may differ in contemporary projects.
- Only open-source projects are included; industrial projects may have different failure distributions, test structures, and CI configurations.

## Construct Validity

- One-to-one failure-to-fault mapping is applied (a test failure = one fault), which may overcount or undercount faults when multiple test failures stem from the same root cause or a single test detects multiple faults.
- APFD is computed without cost weighting (unlike APFDc); this ignores the substantial variation in test execution time across projects and may overstate effectiveness for long-running tests.
- Multiple build types (different platforms, branches) run concurrently and are not always distinguishable at build log level without heuristics; this can introduce interleaving artifacts into the temporal test history.

---

# 10. Limitations

1. Java-only; no multi-language, Python, C/C++, or JavaScript projects.
2. Test granularity is at test class level, not test method level — limits fine-grained prioritization studies.
3. No flaky test identification or filtering; noise from flaky tests is embedded in the failure signal.
4. No APFDc calculation in the baseline; cost-aware evaluation not demonstrated.
5. Data covers only 2007–2016; contemporary CI environments may differ structurally.
6. Baseline micro-study compares only one heuristic against the unmodified order — insufficient for technique comparison purposes; intended only as a starting point.

---

# 11. Future Work

1. **Extended project scope:** Add more projects to improve representativeness; include projects from non-Java ecosystems.
2. **Comparison with proprietary projects:** Assess whether open-source findings transfer to industrial/closed-source settings.
3. **Broader baseline comparison:** Evaluate a wider range of RTP techniques (history-oblivious, code-based, change-based, ML-based) on the dataset.
4. **Confounding factor analysis:** Investigate how real-world noise factors (flaky tests, configuration changes, concurrent builds, hardware variability) affect RTP technique performance.
5. **Inspire human-error-aware heuristics:** The authors suggest that observing human programming activity patterns in real CI data may produce RTP heuristics that complement or outperform formal code–test relations.

---

# 12. Relevance To My Thesis

## Relation Score

Score: **7/10**

## Useful Components

- **Dataset:** RTPTorrent (20 projects) is the primary open-source dataset used by Elsner et al. (2021), which is the most directly relevant paper to the thesis. Citing Mattis et al. 2020 is mandatory when using or referencing RTPTorrent.
- **Evaluation:** APFD baseline values per project (Table 3) provide a reference floor for comparing any new TCP technique. The unmodified order baseline (25.9%) and demonstrated fault effectiveness (81.1%) define the practical range of the evaluation space.
- **Methodology:** The dataset's relational structure (job_id → commit SHA1 → test results) is a reusable template for CI log data extraction pipelines in thesis implementation.
- **Literature survey:** Table 1 (117 papers) is a comprehensive index of the RTP evaluation landscape — directly useful for scoping the thesis's Related Work section.

## Reusable Ideas

1. **Dataset reuse:** Use RTPTorrent directly (or the Elsner et al. 2021 enriched version) as the open-source evaluation corpus for the thesis; cite Mattis et al. 2020 as the dataset source.
2. **APFD as sanity-check baseline:** Report unweighted APFD in addition to APFDc to maintain comparability with the RTPTorrent baseline; use 25.9% (unordered) and 81.1% (demonstrated fault effectiveness) as reference anchors.
3. **Ecological validity argument:** Use Mattis et al.'s literature survey findings (57.9% studies use seeded faults, 19% datasets properly archived) as motivation for using real CI failure data in the thesis evaluation rather than synthetic benchmarks.

## Possible Extensions

1. **APFDc re-evaluation on RTPTorrent:** Re-run the demonstrated fault effectiveness baseline using APFDc (cost-weighted) to produce a cost-aware reference that the thesis can compare against — filling a gap this paper leaves open.
2. **Flaky test impact study:** Implement a flaky test filter on RTPTorrent and measure the change in RTP technique performance — addressing the noise issue this paper flags but does not resolve.
3. **Method-level granularity enrichment:** Supplement RTPTorrent with method-level test data from other sources (e.g., local re-runs) to enable finer-grained feature engineering.

---

# 13. Research Opportunities

| Opportunity | Impact | Difficulty |
| ----------- | ------ | ---------- |
| APFDc re-evaluation of all RTPTorrent projects with cost weighting | Medium — produces more accurate reference baselines | Low |
| Flaky test detection and filtering on RTPTorrent | Medium — removes confounding failure signal | Medium |
| Extend dataset to post-2016 projects using GitHub Actions | High — current CI practices are underrepresented | High |
| Cross-language dataset construction (Python, JS, C++) | High — breaks Java-only limitation | High |
| Method-level granularity enrichment via local CI re-execution | Medium — enables finer feature engineering | High |

---

# 14. Evidence Matrix

## Evidence Supporting Main Claims

| Claim | Supporting Evidence |
| ----- | ------------------- |
| Existing RTP datasets are small and non-representative | Literature survey of 117 papers: mean 5.25 projects/study (SD=6.36); 21.4% use Siemens programs (≤1,000 LOC) |
| Most RTP datasets are not properly archived | 19.0% archived; 83.3% of those only archived because they reuse unmodified SIR datasets |
| Most studies use synthetic/seeded faults | 57.9% use manually seeded faults; only 38.1% use historic real faults |
| Demonstrated fault effectiveness is competitive without code/change data | Avg. APFD: 81.1% prioritized vs. 25.9% original across 20 projects |
| RTPTorrent projects are representative of mature GitHub Java projects | Avg. 11,324 commits / 128 authors vs. GitHub-wide avg. 141 commits / 5 authors |

## Confidence Assessment

**High** (for dataset construction claims and literature survey findings)
**Medium** (for generalizability of baseline results — single heuristic, one metric, Java-only)

Reason: The literature survey is systematic and reproducible (SALSA process, dblp-sourced, 117 papers coded). Dataset construction is documented with sufficient detail for replication. The micro-study is deliberately limited in scope (one heuristic, no comparison with other techniques) and explicitly positioned as a demonstration rather than a comprehensive evaluation.

---

# 15. Citation

## IEEE Citation

T. Mattis, P. Rein, F. Dürsch, and R. Hirschfeld, "RTPTorrent: An Open-source Dataset for Evaluating Regression Test Prioritization," in *Proc. 17th Int. Conf. Mining Software Repositories (MSR '20)*, Seoul, Republic of Korea, Oct. 2020, pp. 385–396. doi: 10.1145/3379597.3387458.

## BibTeX

```bibtex
@inproceedings{Mattis2020,
  author    = {Toni Mattis and Patrick Rein and Falco D{\"u}rsch and Robert Hirschfeld},
  title     = {{RTPTorrent}: An Open-source Dataset for Evaluating Regression Test Prioritization},
  booktitle = {Proceedings of the 17th International Conference on Mining Software Repositories (MSR '20)},
  year      = {2020},
  pages     = {385--396},
  address   = {Seoul, Republic of Korea},
  publisher = {ACM},
  doi       = {10.1145/3379597.3387458},
  url       = {https://doi.org/10.1145/3379597.3387458}
}
```

---

# 16. Personal Notes

## Important Quotes

> "We observed that some datasets are reused, however, many projects study only few projects and these rarely resemble real-world development activity."

> "Only 19.0% of the datasets in the corpus are available through some form of archive."

> "We attribute this property [competitive baseline performance] to the high resolution of our dataset, since we neither considered code nor change-related data as most prioritization techniques do."

> "We hope that using such a dataset can uncover discrepancies between 'clean-room' evaluations and the improvement they bring to real-world testing situations."

## Questions Raised

- How much of the 81.1% prioritized APFD is attributable to projects with high baseline failure rates (e.g., wicket-bootstrap: 32.74 failing TM/build) vs. projects with low rates? Is APFD artificially inflated for high-failure-rate projects?
- The dataset covers 2007–2016. How significantly do CI failure patterns, test suite structures, and build configurations differ in post-2020 Java projects using GitHub Actions?
- Would APFDc results show a different ranking of projects than APFD? (titan with avg. TC Time 68.5s and cloudify at 1.5s likely behave very differently under cost-weighted evaluation.)
- How would the demonstrated fault effectiveness heuristic perform if flaky tests were filtered? Is the 81.1% baseline inflated by high-frequency flaky failures that are easy to predict?

## Follow-up Papers Mentioned

1. Beller et al. 2017 — "TravisTorrent: Synthesizing Travis CI and GitHub for Full-Stack Research on Continuous Integration" — MSR — source dataset for RTPTorrent's raw build logs
2. Gousios 2013 — "The GHTorrent Dataset and Tool Suite" — MSR — source for commit/author metadata linked to RTPTorrent
3. Do, Elbaum, Rothermel 2005 — "Supporting Controlled Experimentation with Testing Techniques: An Infrastructure and its Potential Impact" — ESE — describes SIR, the dominant existing dataset standard
4. Lou et al. 2019 — "A Survey on Regression Test-Case Prioritization" — Advances in Computers — the 2019 RTP survey used as the initial literature seed for the 117-paper corpus
5. Just et al. 2014 — "Defects4J: A Database of Existing Faults" — ISSTA — alternative real-fault Java dataset referenced as a comparator

---

# Final Assessment

## Academic Value

Score: **8/10**

## Practical Value

Score: **7/10**

## Novelty

Score: **7/10**

## Experimental Rigor

Score: **6/10**

## Recommended For

- ✅ Literature Review
- ✅ Thesis Research
- ⬜ Industrial Application (limited: Java-only, 2007–2016 data)
- ✅ Future Extension

## Overall Verdict

Mattis et al. (2020) is a dataset contribution paper rather than a methodology or technique paper. Its primary value lies in establishing an ecologically valid, openly archived evaluation corpus for the RTP community — a gap rigorously documented by the accompanying 117-paper literature survey. For a thesis on AI-driven TCP, RTPTorrent is the standard open-source benchmark to cite and potentially reuse (especially given that Elsner et al. 2021 — the most directly relevant prior work — builds on RTPTorrent for 20 of its 23 projects).

The citation obligation is practical rather than intellectual: any thesis using RTPTorrent data (directly or through Elsner et al.'s enriched version) must cite this paper as the dataset source. Beyond that, the literature survey (Table 1) is genuinely useful for scoping the Related Work section, and the APFD baseline values (25.9% unordered → 81.1% prioritized) serve as quantitative reference anchors for evaluating any new TCP contribution.

The paper's experimental contribution is limited by design — the micro-study evaluates only one heuristic with unweighted APFD, with no comparison against other established techniques. This is an acknowledged scope decision (the paper is a dataset paper, not a technique paper), but it means the baseline provided is insufficient for direct competitive comparison. A thesis using this dataset should compute APFDc baselines from scratch using the Elsner et al. methodology rather than relying on the APFD values reported here.