# Paper Analysis

## Metadata

| Field              | Value                                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| Title              | Revisiting Test-Case Prioritization on Long-Running Test Suites                                         |
| Authors            | Runxiang Cheng; Shuai Wang; Reyhaneh Jabbarvand; Darko Marinov                                          |
| Year               | 2024                                                                                                    |
| Conference/Journal | Proceedings of the 33rd ACM SIGSOFT International Symposium on Software Testing and Analysis, ISSTA ’24 |
| DOI                | 10.1145/3650212.3680307                                                                                 |
| Link               | [https://doi.org/10.1145/3650212.3680307](https://doi.org/10.1145/3650212.3680307)                      |
| Pages              | 13 pages; proceedings pp. 615–627                                                                       |
| Keywords           | Software testing; regression testing; reliability; test prioritization                                  |

Source: 

---

# 1. Executive Summary

## One-Sentence Summary

> The paper introduces LRTS, a recent open-source dataset of long-running CI test suites, and evaluates 59 test-case prioritization techniques, finding that simple hybrid techniques combining fast-test and recent-failure heuristics outperform more sophisticated IR- and learning-based approaches.

## TL;DR

* **Problem:** Long CI test-suite executions delay developer feedback.
* **Research Gap:** Prior TCP studies mostly used outdated, short-running, or inaccessible/proprietary datasets.
* **Proposed Solution:** Build LRTS and empirically evaluate 59 TCP techniques under a unified experimental setup.
* **Main Result:** The best technique is **LatestFail+CC**, with **APFDc = 0.835** on LRTS-DeConf.
* **Key Contribution:** A large dataset of long-running open-source CI test suites plus a broad empirical reassessment of TCP techniques.

---

# 2. Research Problem

## Problem Statement

Continuous integration test suites are becoming longer because software codebases and commit frequency are increasing. Long-running test suites delay feedback to developers, so test-case prioritization is needed to expose failures earlier.

## Motivation

* TCP is more valuable when test suites take hours rather than seconds or minutes.
* Existing TCP conclusions may not transfer to modern long-running CI suites.
* Developers need practical TCP techniques that work on accessible CI data.

## Existing Challenges

* **Challenge 1:** Many previous TCP datasets are outdated or based on short-running test suites.
* **Challenge 2:** Industrial datasets are often inaccessible, proprietary, or domain-specific.
* **Challenge 3:** Confounding failures, especially flaky tests and frequently failing tests, can distort TCP evaluation.

---

# 3. Research Gap

## Gap Explicitly Identified By Authors

* Existing open-source TCP studies mostly use CI builds from over ten years ago.
* Existing datasets often contain test suites that run only for minutes.
* Industrial studies use inaccessible or proprietary projects.
* Prior TCP techniques were studied separately across different datasets and settings.
* There was no recent extensive evaluation of leading TCP techniques under one unified setup.
* There was a lack of high-quality, up-to-date datasets for long-running test suites, where TCP is most useful. 

## Gap Inferred From The Paper

* There is insufficient evidence on whether sophisticated IR-, LTR-, and RTL-based TCP techniques are actually better than simple heuristics for modern long-running CI test suites.
* There is a need to evaluate TCP behavior under realistic noisy CI conditions, including flaky and frequently failing tests.
* There is limited understanding of how TCP techniques handle tests that fail for the first time.

## Why Existing Methods Fail

| Existing Approach               | Limitation                                                                                                                                                           |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code-coverage-based TCP         | Limited applicability because coverage is hard to collect.                                                                                                           |
| Short-running CI datasets       | May not represent long-running suites with more tests, longer test durations, and lower failure ratios.                                                              |
| Proprietary industrial datasets | Inaccessible and difficult to reuse for future research.                                                                                                             |
| IR-based TCP                    | Textual similarity is an imperfect proxy for failure probability; small similarity differences can delay failed tests by hundreds of seconds in long-running suites. |
| History-based TCP               | Weak for tests with no prior failures.                                                                                                                               |
| Outcome-frequency-based TCP     | Strongly affected by flaky or frequently failing tests.                                                                                                              |
| LTR/RTL learning-based TCP      | Requires feature engineering, training, maintenance, and may suffer from distribution shift.                                                                         |

---

# 4. Proposed Method

## Simple Explanation

The authors build a modern dataset of long-running CI test suites, then replay many existing TCP techniques on historical CI builds to measure which ordering strategy finds failures fastest.

## Technical Explanation

The paper constructs **LRTS**, a dataset from Jenkins CI builds of 10 large Apache open-source projects. For each CI build, the authors extract test-suite runs, test outcomes, test durations, stack traces, and code-change information. They then evaluate 59 TCP techniques across time-based, history-based, IR-based, learning-based, and hybrid categories.

## Architecture

Input
↓
Recent Jenkins CI builds, test reports, PR metadata, code diffs, issue tracker data
↓
Processing
↓
Dataset curation, flaky/frequently failing test handling, TCP scoring, test ordering, APFD/APFDc evaluation, statistical analysis
↓
Output
↓
Ranking of TCP techniques, findings on confounding failures, findings on first failures, LRTS dataset release

## Workflow

1. Select 10 large-scale Apache open-source projects with long-running Jenkins CI test suites.
2. Collect CI build metadata, test reports, PR metadata, and code changes.
3. Construct LRTS with 21,255 CI builds and 57,437 test-suite runs.
4. Identify and filter confounding failures using issue trackers, multi-environment TSR comparison, and frequency outlier analysis.
5. Evaluate 59 TCP techniques using APFDc and APFD.
6. Compare techniques under LRTS-All, LRTS-DeConf, and LRTS-FirstFail.
7. Run statistical analysis using ANOVA and Tukey HSD.
8. Revisit prior findings and derive new findings.

## Technologies Used

* **Models:** QTF, MostFail, LatestFail, MostTrans, LatestTrans, TF-FailFreq, TF-TransFreq, IR-BM25, IR-TF-IDF, LTR, RTL.
* **Algorithms:** APFD, APFDc, ANOVA, Tukey HSD, BM25, TF-IDF, gradient boosting regression, reinforcement learning, three-sigma outlier filtering.
* **Dataset:** LRTS.
* **Frameworks:** Jenkins CI; scikit-learn LightGBM implementation.
* **Tools:** Jenkins CI API, GitHub API, JIRA/GitHub issue trackers, Maven, Gradle, CMake.

---

# 5. Experimental Setup

## Dataset

| Dataset        |               Size | Purpose                                              |
| -------------- | -----------------: | ---------------------------------------------------- |
| LRTS-All       | 30,118 failed TSRs | Keeps all test failures.                             |
| LRTS-DeConf    |  9,683 failed TSRs | Removes identified confounding failures.             |
| LRTS-FirstFail |  2,076 failed TSRs | Keeps only the first failure of each non-flaky test. |

LRTS overall contains **21,255 CI builds**, **57,437 test-suite runs**, and **30,118 failed TSRs** from 10 projects. The average TSR duration is **6.5 hours**. 

## Evaluation Metrics

* Accuracy: N/A
* Precision: N/A
* Recall: N/A
* F1: N/A
* AUC: N/A
* Latency: N/A
* Other Metrics:

  * APFD
  * APFDc
  * Failure-to-fault mappings:

    * All failures in one TSR map to the same fault.
    * Each failure in one TSR maps to a unique fault.

## Baseline Methods

1. Random test ordering.
2. Time-based TCP.
3. History-based TCP.
4. IR-based TCP.
5. LTR-based TCP.
6. RTL-based TCP.
7. Cost-cognizant hybrid TCP.

---

# 6. Results

## Quantitative Results

| Method                | Metric                  | Result |
| --------------------- | ----------------------- | -----: |
| QTF-Avg               | APFDc on LRTS-DeConf    |  0.740 |
| QTF-Last              | APFDc on LRTS-DeConf    |  0.739 |
| LatestFail            | APFDc on LRTS-DeConf    |  0.735 |
| LatestTrans           | APFDc on LRTS-DeConf    |  0.728 |
| IR-GitDiff TF-IDF     | APFDc on LRTS-DeConf    |  0.647 |
| LTR with all features | APFDc on LRTS-DeConf    |  0.736 |
| RTL NN-TCFail         | APFDc on LRTS-DeConf    |  0.616 |
| Random                | APFDc on LRTS-DeConf    |  0.502 |
| LatestFail+CC         | APFDc on LRTS-DeConf    |  0.835 |
| QTF-Last              | APFDc on LRTS-FirstFail |  0.798 |
| QTF-Avg               | APFDc on LRTS-FirstFail |  0.796 |
| IR-GitDiff TF-IDF     | APFDc on LRTS-FirstFail |  0.691 |

Table 8 shows that CC and CCH hybrid approaches improve mean APFDc by **9%–41%** and **6%–47%**, respectively; LatestFail+CC obtains the highest APFDc, **0.835**. 

## Key Findings

* Time-based and recent-history-based techniques are highly competitive.
* QTF-Avg and QTF-Last are the best basic techniques by APFDc.
* LTR using all features is competitive but does not beat the best simple hybrid.
* RTL techniques generally underperform LTR and often perform near Random.
* IR-based techniques are weaker than expected on long-running test suites.
* Time-based and IR-based methods work better than history-based methods for first failures. 

## Authors' Claims

* LRTS is the first extensive open-source dataset focused on long-running test suites.
* The study confirms 9 prior findings, refutes 2, and introduces 3 new findings.
* Simple heuristics can outperform sophisticated TCP techniques.
* Prioritizing faster tests that failed recently performs best overall.
* Confounding test failures substantially affect outcome-frequency-based techniques.

---

# 7. Strengths

1. **Strong dataset contribution:** LRTS is recent, open-source, multi-project, and focused on long-running CI test suites.
2. **Broad technique coverage:** The study evaluates 59 TCP techniques across five major categories.
3. **Realistic CI setting:** The dataset uses actual CI failures from real projects rather than synthetic faults.
4. **Confounding failure analysis:** The paper explicitly studies flaky and frequently failing tests.
5. **Statistical testing:** The authors use ANOVA and Tukey HSD to compare techniques.

---

# 8. Weaknesses

1. The study uses only 10 projects, all from Apache Software Foundation.
2. All projects use Jenkins CI, which may limit generalizability to other CI ecosystems.
3. Test prioritization is evaluated at test-class granularity, not method-level or suite-level.
4. The authors do not execute generated test orders due to cost.
5. Flaky test identification depends on issue trackers and heuristic filtering, not full reruns of all failed TSRs.
6. Learning-based methods are omitted from LRTS-FirstFail due to insufficient first-failure data.
7. The evaluation assumes sequential execution for fair comparison, even though CI test suites may run in parallel.

---

# 9. Threats To Validity

## Internal Validity

The authors identify possible bugs in implementation and experimental scripts as internal threats. They address this through unit tests and manual examination. 

## External Validity

The main external threat is generalizability. The authors mitigate it by using real build data from heterogeneous projects, many CI runs, repeated experiments, prior implementations/settings, and statistical analysis. However, the dataset still focuses on 10 Jenkins-based Apache projects. 

## Construct Validity

N/A — the paper does not explicitly provide a separate construct-validity subsection.

---

# 10. Limitations

1. The authors could not rerun all 30,118 failed long-running TSRs multiple times because of resource constraints.
2. Jenkins CI test reports do not include a “flaky” tag even when reruns are used.
3. Multi-environment comparison may misidentify environment-specific failures as flaky.
4. The generated TCP orders are not executed due to high cost.
5. First-failure analysis excludes learning-based techniques.
6. Results may not generalize beyond the studied Jenkins-based Apache projects.
7. Sequential evaluation may not fully represent parallel CI execution.

---

# 11. Future Work

1. The paper explicitly motivates novel TCP techniques that prioritize by history-based heuristics and use time-based or IR-based heuristics to break ties.
2. The paper states that the authors continue collecting build data to preserve CI histories before deletion.
3. N/A — no separate future-work section is provided.

---

# 12. Relevance To My Thesis

## Relation Score

Score: **8/10**

## Useful Components

* **Methodology:** Empirical software engineering dataset construction and large-scale comparative evaluation.
* **Dataset:** LRTS, a reusable dataset of long-running CI test suites.
* **Evaluation:** APFD, APFDc, failure-to-fault mappings, ANOVA, Tukey HSD.
* **Architecture:** CI-data extraction → test-feature construction → prioritization → metric-based evaluation.

## Reusable Ideas

1. Use real CI history instead of synthetic failures.
2. Separate raw data from deconfounded data.
3. Evaluate simple heuristics before adopting complex ML models.
4. Treat flaky and frequently failing tests as confounding variables.
5. Compare techniques under multiple dataset versions.

## Possible Extensions

1. Design a hybrid TCP method that combines recent failure history, test duration, and code-change similarity.
2. Evaluate TCP under parallel CI execution rather than sequential assumptions.
3. Study TCP for enterprise repositories with private CI infrastructure.
4. Add cost-aware ML models that explicitly optimize APFDc.
5. Investigate first-failure prediction using change-aware and time-aware features.

---

# 13. Research Opportunities

| Opportunity                                                      | Impact | Difficulty |
| ---------------------------------------------------------------- | ------ | ---------- |
| Hybrid TCP using history-first ranking with time/IR tie-breaking | High   | Medium     |
| TCP evaluation for parallel CI pipelines                         | High   | High       |
| Flaky-test-aware TCP for enterprise CI                           | High   | Medium     |
| Lightweight TCP for projects without coverage data               | Medium | Low        |
| Distribution-shift-aware LTR TCP                                 | Medium | High       |
| Method-level TCP on long-running test suites                     | Medium | Medium     |
| Cross-CI validation beyond Jenkins                               | High   | Medium     |

---

# 14. Evidence Matrix

## Evidence Supporting Main Claims

| Claim                                             | Supporting Evidence                                                                                                                         |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| LRTS is large and long-running                    | 21,255 CI builds, 57,437 TSRs, 30,118 failed TSRs, average duration 6.5 hours.                                                              |
| Simple time-based techniques are strong           | QTF-Avg APFDc = 0.740 and QTF-Last APFDc = 0.739 on LRTS-DeConf.                                                                            |
| Best overall technique is hybrid                  | LatestFail+CC achieves APFDc = 0.835.                                                                                                       |
| IR-based TCP is weaker than expected              | Best IR-based method, IR-GitDiff TF-IDF, reaches APFDc = 0.647, below QTF and LatestFail.                                                   |
| LTR with all features is competitive              | LTR with all features achieves APFDc = 0.736.                                                                                               |
| History-based methods are weak for first failures | LRTS-FirstFail results show history-based techniques perform similarly to or worse than Random.                                             |
| Confounding failures matter                       | Outcome-frequency-based techniques drop after deconfounding, while recent-history, time-based, and change-aware methods are more resilient. |

## Confidence Assessment

**High**

Reason: The paper provides a clearly described dataset, explicit evaluation settings, quantitative APFDc/APFD results, multiple dataset versions, statistical testing, and a direct summary of confirmed/refuted/new findings.

---

# 15. Citation

## IEEE Citation

R. Cheng, S. Wang, R. Jabbarvand, and D. Marinov, “Revisiting Test-Case Prioritization on Long-Running Test Suites,” in *Proceedings of the 33rd ACM SIGSOFT International Symposium on Software Testing and Analysis (ISSTA ’24)*, Vienna, Austria, 2024, pp. 615–627, doi: 10.1145/3650212.3680307.

## BibTeX

```bibtex
@inproceedings{cheng2024revisiting,
  author    = {Runxiang Cheng and Shuai Wang and Reyhaneh Jabbarvand and Darko Marinov},
  title     = {Revisiting Test-Case Prioritization on Long-Running Test Suites},
  booktitle = {Proceedings of the 33rd ACM SIGSOFT International Symposium on Software Testing and Analysis},
  series    = {ISSTA '24},
  year      = {2024},
  pages     = {615--627},
  publisher = {ACM},
  doi       = {10.1145/3650212.3680307}
}
```

---

# 16. Personal Notes

## Important Quotes

> “The prolonged test suite execution can delay development cycles.”

> “One key challenge in studying TCP is the lack of up-to-date, high-quality datasets.”

## Questions Raised

* Would the ranking change under true parallel CI execution?
* Can LTR be made robust to distribution shift in evolving repositories?
* Can flaky-test detection be automated more accurately without expensive reruns?
* Would method-level TCP produce different results from class-level TCP?
* How would these results transfer to private enterprise systems?

## Follow-up Papers Mentioned

1. Qianyang Peng, August Shi, and Lingming Zhang. “Empirically Revisiting and Enhancing IR-Based Test-Case Prioritization.” ISSTA, 2020.
2. Antonia Bertolino et al. “Learning-to-Rank vs Ranking-to-Learn: Strategies for Regression Testing in Continuous Integration.” ICSE, 2020.
3. Daniel Elsner et al. “Empirically Evaluating Readily Available Information for Regression Test Optimization in Continuous Integration.” ISSTA, 2021.
4. Ahmadreza Saboor Yaraghi et al. “Scalable and Accurate Test Case Prioritization in Continuous Integration Contexts.” TSE, 2022.
5. Emad Fallahzadeh and Peter C. Rigby. “The Impact of Flaky Tests on Historical Test Prioritization on Chrome.” ICSE-SEIP, 2022.
6. Helge Spieker et al. “Reinforcement Learning for Automatic Test Case Prioritization and Selection in Continuous Integration.” ISSTA, 2017.
7. Toni Mattis et al. “RTPTorrent: An Open-source Dataset for Evaluating Regression Test Prioritization.” MSR, 2020.

---

# Final Assessment

## Academic Value

Score: **9/10**

## Practical Value

Score: **8/10**

## Novelty

Score: **8/10**

## Experimental Rigor

Score: **8/10**

## Recommended For

* Literature Review
* Thesis Research
* Industrial Application
* Future Extension

## Overall Verdict

This paper is worth citing for research on regression testing, CI optimization, test-case prioritization, and empirical software engineering. Its strongest contribution is LRTS, a recent and reusable dataset of long-running CI test suites. The paper is also valuable because it challenges the assumption that more sophisticated IR- or ML-based TCP techniques necessarily outperform simple heuristics. The finding that **faster recently failing tests** are the most effective is practical and directly applicable to CI systems. The paper’s treatment of flaky and frequently failing tests is especially useful for realistic evaluation. Its main limitations are the Jenkins/Apache project scope, lack of actual reordered-test execution, and incomplete treatment of first failures for learning-based methods. Overall, it is a strong literature-review anchor paper for any thesis involving CI testing, regression testing, or software engineering automation.
