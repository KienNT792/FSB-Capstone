# Sprint 8 Backlog — Thesis Writing & Submission

**Duration:** Week 15–16  
**Sprint Goal:** Complete thesis submitted to university system; demo script rehearsed; source code repository public.  
**Phase:** Evaluation & Thesis  
**Effort estimate:** ~73h

---

## Definition of Done

- [ ] Thesis PDF ≥ 60 pages, conforming to FSB template, uploaded to university system
- [ ] Abstract in both English and Vietnamese, ≤ 300 words each
- [ ] ≥ 16 IEEE-formatted citations in Zotero, exported as `.bib` (includes RTPTorrent paper)
- [ ] Defense slide deck ≤ 15 slides
- [ ] Demo script runs end-to-end in ≤ 5 minutes (rehearsed)
- [ ] Source code repository public on GitHub with README sufficient to reproduce results

---

## Stories

---

### S8-01 · Chapter 1 — Introduction

**Priority:** Critical  
**Estimate:** 6h

**Description:**  
Write the Introduction chapter establishing the research problem, motivation, research questions, contributions, and thesis structure.

**Acceptance Criteria:**
- Target length: 4–6 pages
- Sections:
  1. **1.1 Background and Motivation** — CI/CD feedback loop problem, cost of slow test suites, information latency concept; cite ≥ 2 industry studies (Microsoft, Google)
  2. **1.2 Problem Statement** — precise statement of what this thesis solves
  3. **1.3 Research Questions** — RQ1, RQ2, RQ3 stated exactly as in the proposal
  4. **1.4 Research Contributions** — 3 numbered contributions matching proposal Section 5
  5. **1.5 Scope and Limitations** — per-project model only; Java/Maven only; JUnit only
  6. **1.6 Thesis Structure** — one sentence per chapter describing its content
- Every claim in Background and Motivation backed by a citation
- No first-person singular ("I"); use "this thesis", "the proposed system", "the study"

---

### S8-02 · Chapter 2 — Literature Review

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Write the Literature Review chapter surveying test prioritization research, ML approaches, and MLOps fundamentals.

**Acceptance Criteria:**
- Target length: 10–14 pages
- Sections:
  1. **2.1 Test Prioritization — Overview** — definition, APFD metric (with formula), classification of approaches (history-based, coverage-based, ML-based)
  2. **2.2 History-Based Approaches** — survey MRF and similar strategies; cite Rothermel 1999 or equivalent foundational paper
  3. **2.3 ML-Based Test Prioritization** — survey ROCKET (Elsner 2021), Bertolino 2020, and ≥ 2 other relevant papers; compare feature sets; note that Elsner 2021 also uses RTPTorrent — position this thesis relative to that work
  4. **2.4 Flaky Test Detection** — definition, impact on CI, existing detection methods
  5. **2.5 MLOps and Model Lifecycle Management** — MLflow, data drift, retraining strategies; cite ≥ 1 MLOps paper
  6. **2.6 Research Gap** — explicit table comparing existing work vs this thesis on: (a) language/ecosystem, (b) feature set, (c) early exit, (d) drift detection, (e) self-hosted
- All claims supported by citations
- Table 2.x: "Summary of Related Work" — rows = papers, columns = key dimensions
- Minimum citations in this chapter: 10

---

### S8-03 · Chapter 3 — Design and Implementation

**Priority:** Critical  
**Estimate:** 12h

**Description:**  
Write the Design and Implementation chapter describing the system architecture, feature engineering, model design, and CI integration.

**Acceptance Criteria:**
- Target length: 16–20 pages
- Sections:
  1. **3.1 System Overview** — architecture diagram (Figure 3.1), description of offline and online pipelines
  2. **3.2 Dataset Construction** — motivation for using RTPTorrent (environment-induced CI failures in live repos), dataset description (Mattis et al. 2020), project selection criteria, CSV loading pipeline, ground truth labelling derivation, dataset statistics table
  3. **3.3 Feature Engineering** — all 4 feature groups described; Table 3.x listing all features with type and description; data leakage prevention strategy explained
  4. **3.4 Model Training** — XGBoost and LightGBM descriptions, preprocessing pipeline, hyperparameter tuning setup, model selection criteria
  5. **3.5 Early Exit Strategy** — confidence-based algorithm (pseudocode or flowchart), threshold selection methodology
  6. **3.6 CI/CD Integration** — GitHub Actions action design, Spring Boot service, webhook flow diagram
  7. **3.7 Feedback Loop and Drift Detection** — PSI formula and threshold, retrain trigger, model hot-swap
- Every diagram referenced as "Figure X.Y" with a caption
- Every table referenced as "Table X.Y" with a caption
- Pseudocode for EarlyExitStrategy included as Algorithm 3.1

---

### S8-04 · Chapter 4 — Results and Discussion

**Priority:** Critical  
**Estimate:** 10h

**Description:**  
Write the Results and Discussion chapter presenting all evaluation data and answering each research question.

**Acceptance Criteria:**
- Target length: 12–16 pages
- Sections:
  1. **4.1 Experimental Setup** — dataset source (RTPTorrent), project selection rationale (Table 4.1: project name, builds, test count, failure rate), split ratios, evaluation environment (hardware specs)
  2. **4.2 RQ1 — Failure Prediction Accuracy** — APFD results table (7 strategies × 5 projects + optimal upper bound), Figure 4.1 (grouped bar chart), statistical test results; direct answer to RQ1 in a dedicated paragraph starting "In answer to RQ1:"
  3. **4.3 RQ2 — Early Exit Effectiveness** — threshold sweep table, Figure 4.2 (tradeoff curve), time reduction results; direct answer to RQ2
  4. **4.4 RQ3 — Drift Detection** — PSI values table, retrain trigger behaviour, APFD before/after retrain; direct answer to RQ3
  5. **4.5 Feature Importance Analysis** — Figure 4.3 (SHAP), discussion of top-5 features
  6. **4.6 Failure Analysis** — ≥ 2 error patterns discussed; ≥ 2 success patterns discussed
  7. **4.7 Threats to Validity** — internal validity (data leakage prevention), external validity (5 Java projects from RTPTorrent, historical TravisCI data only), construct validity (APFD as metric). Note LittleProxy and titan separately as low-failure-rate caveats.
- Each RQ answer paragraph explicitly references the metric values from the results tables
- No new results introduced in Discussion that were not shown in Results tables

---

### S8-05 · Chapter 5 — Conclusion

**Priority:** High  
**Estimate:** 4h

**Description:**  
Write the Conclusion chapter summarising contributions, acknowledging limitations, and suggesting future work.

**Acceptance Criteria:**
- Target length: 3–5 pages
- Sections:
  1. **5.1 Summary of Contributions** — restate the 3 contributions; one paragraph each linking back to results
  2. **5.2 Limitations** — per-project model scope; Java/Maven only; cold-start problem; dataset size; no production deployment
  3. **5.3 Future Work** — ≥ 3 concrete directions: (a) cross-project transfer learning, (b) coverage-based feature integration, (c) real-time CI cost optimisation
- Does not introduce any new claims not supported by Chapter 4

---

### S8-06 · Abstract writing (English and Vietnamese)

**Priority:** Critical  
**Estimate:** 3h

**Description:**  
Write concise abstracts in both languages following academic conventions.

**Acceptance Criteria:**
- English abstract: ≤ 300 words; structure: (1) problem, (2) proposed approach, (3) key results, (4) conclusion
- Vietnamese abstract: translation of English abstract; reviewed for technical term correctness
- Both abstracts mention: APFD metric, CI time reduction percentage, Java ecosystem, MLOps
- Key result values included in abstract (e.g. "APFD of X.XX, representing a Y% improvement over the MRF baseline")

---

### S8-07 · Reference management and IEEE formatting

**Priority:** High  
**Estimate:** 4h

**Description:**  
Ensure all citations are complete, correctly formatted in IEEE style, and consistently applied throughout the thesis.

**Acceptance Criteria:**
- Zotero library contains ≥ 15 entries, all with complete metadata
- Bibliography exported as `docs/references.bib`
- All in-text citations use numbered IEEE format: `[1]`, `[2]`, etc.
- Reference list at end of thesis formatted per IEEE:
  - Journal article format: `Author(s), "Title," Journal, vol., no., pp., Year.`
  - Conference paper format: `Author(s), "Title," in Proc. Conference, Year, pp.`
- No citation appears in reference list without being cited in text
- No in-text citation exists without a corresponding reference list entry
- Tools used: Zotero + Better BibTeX plugin; or manual verification

**Required citations (minimum):**
1. ROCKET (Elsner et al., 2021)
2. Bertolino et al., 2020 — Learning-to-Rank
3. Memon et al., 2017 — Google CI
4. Hilton et al., 2016 — CI costs
5. APFD metric origin paper
6. XGBoost paper (Chen & Guestrin, 2016)
7. LightGBM paper (Ke et al., 2017)
8. MLflow paper or documentation reference
9. Evidently AI (drift detection reference)
10. SHAP (Lundberg & Lee, 2017)
11. Rothermel et al. — test prioritization foundational paper
12. ≥ 3 additional papers from literature review

---

### S8-08 · Thesis formatting and template compliance

**Priority:** Critical  
**Estimate:** 5h

**Description:**  
Apply the FSB thesis template formatting throughout the entire document.

**Acceptance Criteria:**
- Cover page: university logo, thesis title (EN + VI), author name, student ID, supervisor name, submission date
- Table of Contents: auto-generated, includes all headings to level 3, correct page numbers
- List of Figures: all figures listed with captions and page numbers
- List of Tables: all tables listed with captions and page numbers
- Page numbering: Roman numerals for front matter (abstract, TOC); Arabic numerals from Chapter 1
- Font: Times New Roman 13pt body; Arial for headings (or per FSB template spec)
- Line spacing: 1.5 throughout body text
- Margins: per FSB template (typically 3cm left, 2cm other sides for binding)
- Chapter headings: bold, numbered (1., 1.1, 1.1.1)
- Figures: centered, captioned below ("Figure X.Y: Description")
- Tables: centered, captioned above ("Table X.Y: Description")
- Total page count ≥ 60 (excluding references and appendices)

---

### S8-09 · Defense slide deck

**Priority:** High  
**Estimate:** 5h

**Description:**  
Create the presentation slides for the thesis defense, structured to answer committee questions proactively.

**Acceptance Criteria:**
- ≤ 15 slides total
- Slide structure:

| Slide | Content |
|-------|---------|
| 1 | Title, author, date |
| 2 | Agenda |
| 3 | Problem: slow CI feedback loop (1 figure) |
| 4 | Research questions (3 RQs) |
| 5 | System architecture overview (1 diagram) |
| 6 | Feature engineering summary (table, top-5 features) |
| 7 | Model selection: XGBoost vs LightGBM vs Random Forest (comparison table) |
| 8 | RQ1 results: APFD bar chart |
| 9 | RQ2 results: early exit tradeoff curve |
| 10 | RQ3 results: drift detection PSI chart |
| 11 | Demo: screenshot or live demo |
| 12 | Limitations and threats to validity |
| 13 | Contributions summary |
| 14 | Future work (3 bullets) |
| 15 | Q&A |

- Each slide has ≤ 5 bullet points or 1 figure
- All figures are the same plots from `docs/results/plots/` (no new figures)
- Slide notes written for slides 3, 8, 9, 10 (slides likely to attract committee questions)

---

### S8-10 · Source code repository preparation

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Prepare the source code repository for public access with complete documentation.

**Acceptance Criteria:**
- Repository public on GitHub
- `README.md` contains:
  1. Project title and one-paragraph description
  2. System requirements: Python 3.11, Java 11, Docker 24, Maven 3.8
  3. Quick start (5 steps to run demo from scratch)
  4. Repository structure table (directory → purpose)
  5. How to reproduce evaluation results (exact commands)
  6. Link to thesis PDF (if allowed to share)
- All secrets removed: no API keys, no tokens, no passwords in any committed file
- `.env.example` provided with all required environment variables and descriptions
- `data/` directory excluded from repo (too large); `data/README.md` explains how to regenerate it
- All Python dependencies in `requirements.txt` with pinned versions
- Spring Boot `pom.xml` has no SNAPSHOT dependencies
- `LICENSE` file present (MIT recommended)

---

### S8-11 · Final review and submission

**Priority:** Critical  
**Estimate:** 4h

**Description:**  
Final quality check of the thesis document before submission.

**Acceptance Criteria:**
- Spell check run on full document (zero unresolved spelling errors)
- All figure and table references verified: every "Figure X.Y" and "Table X.Y" in text matches an actual figure/table
- All "TODO", "TBD", "[INSERT]" placeholders removed
- Page count confirmed ≥ 60
- PDF generated from final `.docx` or LaTeX source; PDF file size ≤ 50MB
- PDF uploaded to university system; confirmation screenshot saved to `docs/submission-confirmation.png`
- Supervisor notified of submission via email

---

## Sprint 8 — Dependency Map

```
S8-01 (Ch1) ──┐
S8-02 (Ch2) ──┤
S8-03 (Ch3) ──┼──→ S8-08 (formatting) ──→ S8-11 (submission)
S8-04 (Ch4) ──┤
S8-05 (Ch5) ──┘

S8-06 (abstract) ──→ S8-08
S8-07 (references) ──→ S8-04, S8-08
S8-09 (slides) — independent, can be done in parallel
S8-10 (repo) — independent, can be done in parallel
```

---

## Writing Schedule (recommended)

| Day | Task |
|-----|------|
| W15 Mon–Tue | S8-01 (Ch1), S8-07 (references setup) |
| W15 Wed–Thu | S8-02 (Ch2) |
| W15 Fri | S8-03 (Ch3, sections 3.1–3.4) |
| W16 Mon | S8-03 (Ch3, sections 3.5–3.7), S8-06 (abstract) |
| W16 Tue | S8-04 (Ch4) |
| W16 Wed | S8-05 (Ch5), S8-09 (slides) |
| W16 Thu | S8-08 (formatting), S8-10 (repo) |
| W16 Fri | S8-11 (final review + submission) |

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Chapter 3 too long (> 20 pages) | Medium | Low | Move implementation detail to Appendix; keep Chapter 3 high-level |
| Supervisor requests major revision to Chapter 4 | Medium | High | Submit Ch1–3 draft by end of W15; allow W16 Mon for revisions before Ch4 is written |
| University submission system down | Low | Critical | Submit 24 hours before deadline; have backup PDF ready to email |
| Thesis < 60 pages after formatting | Low | Medium | Expand Section 3.3 (feature engineering) and Section 4.7 (threats to validity) |
| Missing citation for a key claim | Medium | Medium | Every claim in Ch1–2 must have a citation note during drafting; do not leave for final review |
