# Paper Analysis

## Metadata

| Field              | Value                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| Title              | Learning-to-Rank vs Ranking-to-Learn: Strategies for Regression Testing in Continuous Integration |
| Authors            | Antonia Bertolino; Antonio Guerriero; Breno Miranda; Roberto Pietrantuono; Stefano Russo          |
| Year               | 2020                                                                                              |
| Conference/Journal | 42nd International Conference on Software Engineering — ICSE ’20                                  |
| DOI                | 10.1145/3377811.3380369                                                                           |
| Link               | [https://doi.org/10.1145/3377811.3380369](https://doi.org/10.1145/3377811.3380369)                |
| Pages              | 12                                                                                                |
| Keywords           | Regression testing; test selection; test prioritization; continuous integration; machine learning |

Source: uploaded PDF. 

---

# 1. Executive Summary

## One-Sentence Summary

> The paper compares Learning-to-Rank and Reinforcement-Learning-based Ranking-to-Learn strategies for machine-learning-based regression test selection and prioritization in Continuous Integration.

## TL;DR

* **Problem:** CI regression testing is constrained by short inter-commit times, making it difficult to run all relevant tests.
* **Research Gap:** Existing ML-based regression test prioritization lacks clear criteria for selecting the most suitable ML strategy or algorithm for a given CI context.
* **Proposed Solution:** Use static class-level test selection followed by ML-based test prioritization, comparing 10 algorithms across LTR and RTL strategies.
* **Main Result:** MART and LambdaMART achieve the best ranking effectiveness; pairwise LTR performs best overall in RPA; ensemble methods outperform non-ensemble methods.
* **Key Contribution:** The paper provides empirical criteria for choosing ML-based regression test prioritization algorithms based on effectiveness, cost, code variability, failure proneness, inter-commit time, and history length.

---

# 2. Research Problem

## Problem Statement

Continuous Integration requires frequent regression testing after commits, but test suites may be too large to execute fully within the available time. The paper addresses how to select relevant tests and prioritize them effectively using machine learning.

## Motivation

* CI environments have frequent commits and short feedback cycles.
* Traditional regression testing reduction techniques may not scale to modern CI.
* Test selection alone may still leave too many tests to run.
* Prioritization without selection may waste effort on irrelevant tests.
* ML-based prioritization is promising, but practitioners lack evidence-based guidance for choosing between LTR and RTL strategies. 

## Existing Challenges

* Dynamic coverage collection is expensive and potentially impractical in CI.
* CI environments are dynamic: tests can be added or removed, and testing focus can change.
* Supervised LTR models may become less representative when the CI context changes.
* RL/RTL methods adapt online but may have higher training cost.
* Existing ML-based approaches do not provide enough comparative evidence across algorithm families.

---

# 3. Research Gap

## Gap Explicitly Identified By Authors

* There is a lack of criteria for choosing the most appropriate ML technique for regression test prioritization in a given CI situation.
* No prior experimental study comprehensively compared LTR and RTL test prioritization algorithms in CI.
* Nine of the ten evaluated ML algorithms had not previously been used for test prioritization.
* The influence of code-under-test features and CI process features on algorithm effectiveness had not been sufficiently studied. 

## Gap Inferred From The Paper

* A practical CI test prioritization method must consider both ranking effectiveness and operational cost.
* Algorithm choice should depend on context-specific constraints, not only average predictive performance.
* Static ML models may be unsuitable for highly variable CI environments unless retrained.
* Online-learning RTL may be useful when adaptability matters more than raw ranking performance.

## Why Existing Methods Fail

| Existing Approach                     | Limitation                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Traditional regression test reduction | May not scale to modern CI due to large codebases, large test suites, and high environment dynamicity. |
| Dynamic coverage-based test selection | Expensive due to runtime overhead, instrumentation, and coverage maintenance.                          |
| Test selection alone                  | May still select more tests than can be executed under short inter-commit times.                       |
| Prioritization without selection      | May rank tests irrelevant to the current commit.                                                       |
| LTR-only approaches                   | Require prior training and may lose predictive ability when the operating context changes.             |
| Previous RL approaches                | Were not comprehensively compared with LTR strategies and algorithm families.                          |

---

# 4. Proposed Method

## Simple Explanation

The paper first uses static dependency analysis to select only test classes related to changed code. Then, it applies machine learning to rank those selected test classes so that failing and faster tests are executed earlier.

## Technical Explanation

The proposed TS&P process has two stages:

1. **Static test selection**

   * Builds a class-level dependency graph.
   * Detects changed classes after each commit.
   * Finds classes transitively dependent on changed classes.
   * Selects associated test classes as test targets.

2. **ML-based test prioritization**

   * Ranks selected test targets.
   * Primary criterion: fault detection.
   * Secondary criterion: execution time.
   * Optimal ranking: failing test targets first; within failing and non-failing groups, shorter tests first.
   * Compares:

     * LTR pointwise algorithms,
     * LTR pairwise algorithms,
     * LTR listwise algorithms,
     * RTL reinforcement learning algorithms.

Figure 1 in the paper illustrates the overall selection-then-prioritization pipeline. 

## Architecture

```text
Input
- Changed source classes
- Class-level dependency graph
- Test classes
- Code metrics
- Test execution history

↓

Processing
- Update dependency graph
- Select affected test targets
- Extract code/test features
- Apply LTR or RTL prioritization algorithm
- Rank selected test targets

↓

Output
- Prioritized list of selected regression test targets
```

## Workflow

1. Build or update a class-level dependency graph.
2. Identify changed classes in the current commit.
3. Select test classes transitively related to changed classes.
4. Extract code and test-history features.
5. Train or update the ML model depending on the strategy.
6. Rank selected test targets.
7. Execute tests according to the produced ranking.

## Technologies Used

* **Models:**

  * K-Nearest Neighbor — KNN
  * Random Forest — RF
  * LambdaMART — L-MART
  * MART
  * RankBoost
  * RankNet
  * Coordinate Ascent — CA
  * Reinforcement Learning shallow network — RL
  * Reinforcement Learning multilayer perceptron — RL-MLP
  * Reinforcement Learning Random Forest — RL-RF

* **Algorithms:**

  * Static class-level dependency analysis
  * Learning-to-Rank: pointwise, pairwise, listwise
  * Reinforcement Learning / Ranking-to-Learn
  * Experience replay
  * Principal Component Analysis
  * Principal Feature Analysis
  * Hotelling’s multivariate control charts
  * Transfer entropy
  * Friedman test with Iman-Davenport extension
  * Shaffer post hoc test
  * Mann-Whitney-Wilcoxon test
  * Wilcoxon signed-rank test

* **Dataset:**

  * Six Apache Commons Java projects.

* **Frameworks:**

  * Maven
  * Java

* **Tools:**

  * SCITools Understand 2.0
  * Weka
  * Knime
  * RankLib
  * Python implementation for RTL
  * Java/Maven test-selection implementation

---

# 5. Experimental Setup

## Dataset

| Dataset                 | Size                                             | Purpose                     |
| ----------------------- | ------------------------------------------------ | --------------------------- |
| Apache Commons Codec    | 614 commits; 14.8 KLoC; 39 targets; 403 tests    | Subject for TS&P evaluation |
| Apache Commons Compress | 627 commits; 34.5 KLoC; 94 targets; 475 tests    | Subject for TS&P evaluation |
| Apache Commons Imaging  | 376 commits; 40.3 KLoC; 79 targets; 90 tests     | Subject for TS&P evaluation |
| Apache Commons IO       | 387 commits; 28.6 KLoC; 95 targets; 1014 tests   | Subject for TS&P evaluation |
| Apache Commons Lang     | 521 commits; 77.8 KLoC; 163 targets; 3899 tests  | Subject for TS&P evaluation |
| Apache Commons Math     | 111 commits; 186.7 KLoC; 497 targets; 4864 tests | Subject for TS&P evaluation |

The subjects are Java projects from Apache Commons using Maven, selected based on size greater than 10 KLoC, more than 100 latest working commits, and more than five mean test targets per commit. 

## Evaluation Metrics

* **Accuracy:** N/A
* **Precision:** N/A
* **Recall:** N/A
* **F1:** N/A
* **AUC:** N/A
* **Latency:** Ranking time, training time, test selection time, test execution time, end-to-end time.
* **Other Metrics:**

  * RPA — Rank Percentile Average.
  * Normalized RPA.
  * Difference between predicted and optimal test execution time under 25%, 50%, and 75% test-budget scenarios.
  * Difference between predicted and optimal number of failing tests under 25%, 50%, and 75% test-budget scenarios.

The authors explicitly discard APFD because CI focuses on feedback for individual test cases and because the number of faults per release is small in their dataset. 

## Baseline Methods

1. Static class-level test selection without ML ranking.
2. LTR pointwise algorithms:

   * KNN
   * RF
3. LTR pairwise algorithms:

   * LambdaMART
   * MART
   * RankBoost
   * RankNet
4. LTR listwise algorithm:

   * Coordinate Ascent
5. RTL algorithms:

   * RL
   * RL-MLP
   * RL-RF

---

# 6. Results

## Quantitative Results

| Method / Factor           | Metric                         | Result                                                                          |
| ------------------------- | ------------------------------ | ------------------------------------------------------------------------------- |
| MART                      | RPA                            | Best-performing group                                                           |
| LambdaMART                | RPA                            | Best-performing group                                                           |
| RF, RL-RF, RankBoost      | RPA                            | Follow MART and LambdaMART, with no significant differences reported among them |
| RL-MLP, CA, RL            | RPA                            | Worst group, but average RPA values remain above 0.8                            |
| KNN                       | Ranking time                   | Longest ranking time                                                            |
| CA                        | Ranking time                   | Best ranking time                                                               |
| Algorithm comparison      | RPA and ranking time           | Significant difference; p-value < 2.2E-16                                       |
| Strategy comparison       | RPA and ranking time           | Significant difference; p-value < 2.2E-16                                       |
| Pairwise LTR              | RPA                            | Best strategy                                                                   |
| Listwise LTR / CA         | Ranking time                   | Best ranking-time strategy                                                      |
| Ensemble algorithms       | Average RPA                    | 0.927                                                                           |
| Non-ensemble algorithms   | Average RPA                    | 0.869                                                                           |
| Ensemble algorithms       | Average ranking time           | 7.206 ms                                                                        |
| Non-ensemble algorithms   | Average ranking time           | 10.376 ms                                                                       |
| Ensemble vs non-ensemble  | RPA and prioritization time    | Significant difference; p-value < 2.2E-16                                       |
| PFA feature selection     | Feature reduction              | 10 of 50 features selected                                                      |
| PFA feature selection     | Variance retained              | 20% of features retain 90% of original data variance                            |
| History length            | RPA                            | RPA is quite insensitive above 500 observations                                 |
| Time-constrained scenario | Best execution-time difference | MART: 0.0164 at 25%, 0.0386 at 50%, 0.0193 at 75%                               |
| Time-constrained scenario | Best failing-test difference   | RankBoost: -1.3333 at 25%, RankBoost: -1.1667 at 50%, RF: -1.0500 at 75%        |

## Key Findings

* MART and LambdaMART offer the best ranking effectiveness.
* Pairwise LTR is the strongest overall learning strategy.
* Ensemble algorithms are better than non-ensemble algorithms in both RPA and ranking time.
* RTL methods are more robust to code variability, likely due to online learning.
* RTL methods require longer training time because training occurs at each commit.
* A small set of features can preserve most of the feature variance.
* Short inter-commit time can change the preferred algorithm because RPA alone does not capture time-constrained execution behavior.
* Training sample sizes greater than 500 observations provide little RPA improvement but increase training time. 

## Authors' Claims

* ML prioritization after static test selection is valuable under short inter-commit times.
* The testing criteria and their relative weight should be defined before choosing an algorithm.
* Feature selection can be performed algorithm-independently to simplify the selection process.
* Practitioners should first choose the learning strategy and algorithm category, then choose the concrete algorithm.
* Algorithm tuning is necessary because default parameters may not provide optimal results. 

---

# 7. Strengths

1. **Direct comparison of LTR and RTL**

   * The paper compares two broad ML strategies in the same CI regression testing setting.

2. **Broad algorithm coverage**

   * Evaluates 10 algorithms across pointwise LTR, pairwise LTR, listwise LTR, and RTL.

3. **Cost-aware analysis**

   * Measures ranking time, training time, selection time, execution time, and end-to-end time.

4. **Context-sensitive analysis**

   * Studies code variability, failure proneness, feature importance, inter-commit time, and history length.

5. **Practical guidelines**

   * Produces concrete recommendations for choosing ML algorithms under CI constraints.

6. **Replication support**

   * Authors report that code, settings, and additional results are publicly available. 

---

# 8. Weaknesses

1. **Limited subject diversity**

   * Only six Java projects from Apache Commons are used.

2. **Low failure density**

   * Failing test targets and failing tests are very rare in the original dataset.

3. **Artificial failure injection**

   * Failure-proneness analysis uses injected failing outcomes rather than real production faults.

4. **New evaluation metric**

   * RPA is introduced by the authors; conclusions may differ under another metric.

5. **Default parameter settings**

   * Algorithm performance may change with tuning.

6. **No industrial validation**

   * The studied projects are open-source and may not represent industrial CI environments.

7. **No dynamic coverage comparison**

   * The approach intentionally avoids dynamic coverage because of CI overhead.

---

# 9. Threats To Validity

## Internal Validity

* Tool settings and algorithm parameter choices may affect results.
* Default parameter values were used for fair comparison, but tuning could change algorithm rankings.
* Some experimental design choices may bias comparisons differently across algorithms.
* Artificial failure injection may not behave like real faults in production. 

## External Validity

* Experiments use only six Java Apache Commons projects.
* Results may not generalize to:

  * industrial systems,
  * non-Java systems,
  * non-Maven projects,
  * non-open-source development processes,
  * larger CI infrastructures. 

## Construct Validity

* RPA is a new metric; using another metric might change RQ1 results.
* Cost-related analyses may also depend on metric design.
* The selected CUT and CI-process characteristics may not fully capture all relevant factors influencing regression testing performance. 

---

# 10. Limitations

1. Evaluation is restricted to six Java Apache Commons projects.
2. The paper does not validate results on industrial CI pipelines.
3. The dataset contains highly imbalanced failure distributions.
4. Failure-proneness analysis relies on artificial failure injection.
5. Dynamic coverage-based selection/prioritization is excluded.
6. Algorithm parameters are mostly default values.
7. RPA is not an established regression testing metric.
8. Time-constrained scenarios are limited to 25%, 50%, and 75% of selected test targets.

---

# 11. Future Work

1. Replicate the study on more subjects.
2. Evaluate other programming languages.
3. Evaluate non-open-source and industrial CI processes.
4. Explore additional ML algorithms.
5. Investigate stronger or more aggressive time-constrained scenarios.
6. Study algorithm-specific feature selection.
7. Tune algorithms using grid search, randomized search, or similar methods.
8. Validate failure-proneness conclusions with real faults rather than injected failures.

---

# 12. Relevance To My Thesis

## Relation Score

Score: **8/10**
Scope: thesis work on ML-based regression testing, test case prioritization, CI optimization, or AI for software engineering.

## Useful Components

* **Methodology:**

  * Selection-then-prioritization pipeline.
  * Comparative evaluation of ML strategies.
  * Cost-effectiveness analysis in CI.

* **Dataset:**

  * Six Apache Commons Java projects.
  * Commit-level CI-style regression testing data.

* **Evaluation:**

  * RPA for ranking quality.
  * Training/ranking/selection/execution time.
  * Time-constrained test budget scenarios.

* **Architecture:**

  * Static dependency graph.
  * Test target selection.
  * Feature extraction.
  * ML ranking.

## Reusable Ideas

1. Use static dependency analysis before ML ranking to reduce problem size.
2. Treat test prioritization as a ranking problem rather than simple classification.
3. Compare pointwise, pairwise, listwise, and reinforcement-learning strategies.
4. Evaluate both ranking effectiveness and CI runtime cost.
5. Analyze model behavior under code variability and failure imbalance.
6. Use feature selection to reduce model input dimensionality.

## Possible Extensions

1. Apply the same comparison to GitHub Actions or Jenkins projects.
2. Replace RPA with APFDc/APFDC and compare conclusions.
3. Evaluate industrial monorepos with longer-running test suites.
4. Combine static selection with execution-history-only lightweight prioritization.
5. Investigate online learning with lower training overhead.
6. Compare LTR/RTL with modern gradient boosting and neural ranking models.

---

# 13. Research Opportunities

| Opportunity                                                         | Impact | Difficulty |
| ------------------------------------------------------------------- | ------ | ---------- |
| Replicate LTR vs RTL on industrial CI datasets                      | High   | High       |
| Compare RPA against APFDc/APFDC in CI                               | Medium | Medium     |
| Extend to GitHub Actions / Jenkins pipelines                        | High   | Medium     |
| Study method-level instead of class-level dependency selection      | High   | High       |
| Build adaptive strategy selector for CI test prioritization         | High   | High       |
| Use real failure datasets instead of injected failures              | High   | High       |
| Tune algorithms systematically and compare against default settings | Medium | Medium     |
| Evaluate hybrid static + lightweight dynamic dependency collection  | High   | High       |

---

# 14. Evidence Matrix

## Evidence Supporting Main Claims

| Claim                                                   | Supporting Evidence                                                                                               |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| CI test prioritization needs context-aware ML choice    | Authors state that criteria for choosing the most appropriate technique are lacking.                              |
| Pairwise LTR performs best overall                      | Pairwise algorithms have the best RPA among the four strategy groups.                                             |
| MART and LambdaMART are top algorithms                  | Authors report MART and LambdaMART as best in terms of RPA.                                                       |
| Ensemble methods outperform non-ensemble methods        | Ensemble RPA = 0.927 vs non-ensemble RPA = 0.869; ranking time = 7.206 ms vs 10.376 ms.                           |
| RTL is more robust to code variability                  | Transfer entropy analysis ranks RL-based algorithms as less affected by code variability.                         |
| Feature reduction is feasible                           | PFA selected 10 of 50 features while retaining 90% variance.                                                      |
| History beyond 500 observations adds little RPA benefit | RPA is reported as insensitive above 500 observations.                                                            |
| Short inter-commit time changes algorithm choice        | Under 25/50/75% budget scenarios, the best algorithm depends on execution-time and failure-detection differences. |

## Confidence Assessment

**High**

Reason:

* The paper explicitly reports research questions, algorithms, subjects, metrics, statistical tests, and quantitative results.
* Main conclusions are supported by tables and statistical comparisons.
* Confidence is lower for generalization beyond Java Apache Commons projects because the authors explicitly identify this as an external-validity threat.

---

# 15. Citation

## IEEE Citation

A. Bertolino, A. Guerriero, B. Miranda, R. Pietrantuono, and S. Russo, “Learning-to-Rank vs Ranking-to-Learn: Strategies for Regression Testing in Continuous Integration,” in *Proceedings of the 42nd International Conference on Software Engineering (ICSE ’20)*, Seoul, Republic of Korea, 2020, doi: 10.1145/3377811.3380369.

## BibTeX

```bibtex
@inproceedings{bertolino2020learning,
  title     = {Learning-to-Rank vs Ranking-to-Learn: Strategies for Regression Testing in Continuous Integration},
  author    = {Bertolino, Antonia and Guerriero, Antonio and Miranda, Breno and Pietrantuono, Roberto and Russo, Stefano},
  booktitle = {Proceedings of the 42nd International Conference on Software Engineering (ICSE '20)},
  year      = {2020},
  publisher = {ACM},
  address   = {New York, NY, USA},
  numpages  = {12},
  doi       = {10.1145/3377811.3380369}
}
```

---

# 16. Personal Notes

## Important Quotes

> “we still lack criteria for choosing the most appropriate technique”

> “Nine of the ten ML algorithms have never been used before for test prioritization.”

> “The RPA is quite insensitive with respect to a training sample size bigger than 500 observations.”

These quotes are from the uploaded paper.  

## Questions Raised

* Would MART and LambdaMART remain best on larger industrial CI systems?
* Would RPA conclusions remain stable under APFDc or APFDC?
* How much does hyperparameter tuning change the algorithm ranking?
* Would RTL become more competitive in systems with higher code/test volatility?
* How would the results change with real fault data instead of injected failures?

## Follow-up Papers Mentioned

1. Busjaeger and Xie — Learning for Test Prioritization: An Industrial Case Study.
2. Spieker et al. — Reinforcement-learning-based test prioritization and selection.
3. Lachmann et al. — LTR SVM-Rank for black-box prioritization.
4. Legunsen et al. — class-level regression test selection.
5. Elbaum et al. — history-based test selection and prioritization in CI.

---

# Final Assessment

## Academic Value

Score: **8/10**

## Practical Value

Score: **8/10**

## Novelty

Score: **8/10**

## Experimental Rigor

Score: **7.5/10**

## Recommended For

* Literature Review: **Yes**
* Thesis Research: **Yes**
* Industrial Application: **Partially, requires validation**
* Future Extension: **Yes**

## Overall Verdict

This paper is worth citing for research on ML-based regression testing in Continuous Integration. Its main value is the structured comparison between Learning-to-Rank and Ranking-to-Learn strategies, rather than proposing a single new model. The study provides useful empirical evidence that pairwise LTR, especially MART and LambdaMART, performs strongly for test prioritization after static test selection. It also shows that ensemble methods can outperform non-ensemble methods in both ranking quality and ranking time. The practical guidelines are valuable because they connect algorithm choice with CI constraints such as inter-commit time, code variability, history length, and feature availability. The main limitation is external validity: all subjects are Java Apache Commons projects, not industrial systems. The paper is highly relevant for thesis work on AI-based regression testing, CI optimization, and empirical software engineering.
