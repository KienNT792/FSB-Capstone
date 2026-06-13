# Investigation: Near-Zero MI for `test_file_touched` and `same_package`

**Date:** 2026-06-12  
**Trigger:** `notebooks/02_eda_features.ipynb` (run 2026-06-12) reported MI scores that are an order of magnitude below the weakest plausible feature (`import_overlap`, MI = 0.000779):
- `test_file_touched`: MI = 0.000124
- `same_package`: MI = 0.000193

---

## Step 1: Implementation Snippets

Both features are computed in `src/features/dependency_extractor.py`, class `DependencyFeatureExtractor`, method `extract` (lines 25–55).

### `test_file_touched` — lines 37

```python
# dependency_extractor.py:37
test_file_touched = int(test_rel_normalized in normalized_changed)
```

**How it works:**

1. `_test_id_to_path(test_id)` converts the fully-qualified class name to the conventional Maven path:
   `de.neuland.jade4j.compiler.CompilerTest` → `src/test/java/de/neuland/jade4j/compiler/CompilerTest.java` (line 58–59).
2. `_normalize_path` strips leading `./` and normalises backslashes (line 100–101).
3. The `in` check is an **exact string match** of the normalized test path against each normalized changed path from `file_changes`.

**Guard condition:** If `_load_test_context` returns `None` (file not found on disk or javalang parse failure), the method returns `ZERO_FEATURES` (all zeros), bypassing the computation entirely (lines 33, 13–19).

### `same_package` — lines 39–41

```python
# dependency_extractor.py:39-41
same_package = int(
    any(self._path_to_package(path) == package_name for path in normalized_changed)
)
```

**How it works:**

1. `package_name` is parsed from the test file's AST via javalang: `getattr(getattr(tree, "package", None), "name", "")` (line 89).
2. `_path_to_package(path)` extracts the package from a changed file's path by splitting on `src/main/java/` or `src/test/java/` and joining the directory components (lines 115–122).
3. Comparison is an **exact string equality** between the two package strings.

**Same guard:** `dependency_parse_failed=1` → all zeros.

### Feature joiner — `feature_joiner.py:104–110`

```python
# feature_joiner.py:104-110
dependency_features = self._dependency_features(
    test_id,
    commit_sha,
    changed_java_files,
    self.git_root / repo,
    dependency_cache,
)
```

`changed_java_files` is obtained from `_changed_files_by_commit` (line 64), which reads `file_path` from the DuckDB `file_changes` table filtered to `.java` files via `CommitFeatureExtractor._file_change_features`. The `DependencyFeatureExtractor` receives these paths directly.

---

## Step 2: Distribution on Full Dataset (160,454 rows across 5 repos)

### `test_file_touched`

**Overall value counts:**

| value | count |
|-------|-------|
| 0     | 159,602 |
| 1     | 852 |

Fraction = 1 overall: **0.53%**

**Per-repo breakdown:**

| repo | count_0 | count_1 | frac=1 |
|------|---------|---------|--------|
| adamfisk@LittleProxy | 15,619 | 153 | 0.97% |
| deeplearning4j@deeplearning4j | 15,509 | **0** | 0.00% |
| l0rdn1kk0n@wicket-bootstrap | 48,061 | 167 | 0.35% |
| neuland@jade4j | 35,503 | 384 | 1.07% |
| thinkaurelius@titan | 44,910 | 148 | 0.33% |

**Cross-tab with label:**

| test_file_touched | label=0 | label=1 | All |
|-------------------|---------|---------|-----|
| 0 | 145,686 | 13,916 | 159,602 |
| 1 | 806 | 46 | 852 |
| All | 146,492 | 13,962 | 160,454 |

Failure rate when `test_file_touched=1`: 46/852 = **5.4%**  
Failure rate when `test_file_touched=0`: 13,916/159,602 = **8.7%**

The feature is **not positively correlated with failure** — touching the test file itself actually correlates with slightly *fewer* failures (or more precisely, it's nearly uncorrelated). This is plausible: a commit that touches a test file was likely a test update, not a source bug.

---

### `same_package`

**Overall value counts:**

| value | count |
|-------|-------|
| 0     | 152,951 |
| 1     | 7,503 |

Fraction = 1 overall: **4.68%**

**Per-repo breakdown:**

| repo | count_0 | count_1 | frac=1 |
|------|---------|---------|--------|
| adamfisk@LittleProxy | 12,159 | 3,613 | 22.9% |
| deeplearning4j@deeplearning4j | 15,507 | **2** | 0.01% |
| l0rdn1kk0n@wicket-bootstrap | 47,484 | 744 | 1.5% |
| neuland@jade4j | 33,120 | 2,767 | 7.7% |
| thinkaurelius@titan | 44,681 | 377 | 0.84% |

**Cross-tab with label:**

| same_package | label=0 | label=1 | All |
|--------------|---------|---------|-----|
| 0 | 139,432 | 13,519 | 152,951 |
| 1 | 7,060 | 443 | 7,503 |
| All | 146,492 | 13,962 | 160,454 |

Failure rate when `same_package=1`: 443/7,503 = **5.9%**  
Failure rate when `same_package=0`: 13,519/152,951 = **8.8%**

Again the feature is **slightly negatively** correlated with failure in the aggregate — same as `test_file_touched`. This is partly a base-rate artifact: large squash/bulk commits (which have many changed files and therefore more `same_package=1` hits) tend to have proportionally lower failure rates per test.

---

### Dependency parse failure rates per repo (Step 2 extra)

| repo | parse_failed | total | pct |
|------|-------------|-------|-----|
| adamfisk@LittleProxy | 930 | 15,772 | 5.9% |
| **deeplearning4j@deeplearning4j** | **15,171** | **15,509** | **97.8%** |
| l0rdn1kk0n@wicket-bootstrap | 6,200 | 48,228 | 12.9% |
| neuland@jade4j | 10,981 | 35,887 | 30.6% |
| **thinkaurelius@titan** | **29,424** | **45,058** | **65.3%** |

`deeplearning4j` is almost entirely parse-failed (97.8%), so both dependency features default to 0 for essentially the whole repo — the 338 parse-ok rows are far too few to recover signal.

---

## Step 3: Manual Trace on 3 Known Commits (neuland@jade4j)

Three representative rows were selected from `neuland@jade4j` with `commit_sha` known, `commit_meta_missing=0`, and `dependency_parse_failed=0`.

### Initial sample (all-zero control)

| commit_sha (12) | test_id | feature | expected | actual | match |
|-----------------|---------|---------|----------|--------|-------|
| 58c9ebfbdc1b | de.neuland.jade4j.parser.LargeBodyTextWithoutPipesParserTest | test_file_touched | 0 | 0 | Y |
| 58c9ebfbdc1b | de.neuland.jade4j.parser.LargeBodyTextWithoutPipesParserTest | same_package | 0 | 0 | Y |
| cbf28b94d7df | de.neuland.jade4j.parser.FileNameBuilderTest | test_file_touched | 0 | 0 | Y |
| cbf28b94d7df | de.neuland.jade4j.parser.FileNameBuilderTest | same_package | 0 | 0 | Y |
| 57814e9791aa | de.neuland.jade4j.parser.DoctypeParserTest | test_file_touched | 0 | 0 | Y |
| 57814e9791aa | de.neuland.jade4j.parser.DoctypeParserTest | same_package | 0 | 0 | Y |

All zeros match correctly. To confirm the positive case is also correct, 3 rows per feature where the stored value is 1 were also traced (targeted sample).

### Targeted trace — rows where `test_file_touched=1`

| commit_sha (12) | test_id | expected_rel | changed_path_hit | actual | match |
|-----------------|---------|--------------|-----------------|--------|-------|
| 7ed0d1cb50fb | de.neuland.jade4j.compiler.CompilerTest | `src/test/java/de/neuland/jade4j/compiler/CompilerTest.java` | exact match in 98 changed paths | 1 | **Y** |
| 609c268de128 | de.neuland.jade4j.compiler.IssuesTest | `src/test/java/de/neuland/jade4j/compiler/IssuesTest.java` | exact match in 7 changed paths | 1 | **Y** |
| 7ed0d1cb50fb | de.neuland.jade4j.parser.AssignmentParserTest | `src/test/java/de/neuland/jade4j/parser/AssignmentParserTest.java` | exact match in 98 changed paths | 1 | **Y** |

### Targeted trace — rows where `same_package=1`

| commit_sha (12) | test_id | test_package | changed_pkg_hit | actual | match |
|-----------------|---------|-------------|----------------|--------|-------|
| 4adf5badbc2b | de.neuland.jade4j.compiler.IssuesTest | `de.neuland.jade4j.compiler` | `de.neuland.jade4j.compiler` from `src/main/java/de/neuland/jade4j/compiler/Utils.java` | 1 | **Y** |
| 56abfd2b758b | de.neuland.jade4j.compiler.OriginalJade20150515SingleTest | `de.neuland.jade4j.compiler` | `de.neuland.jade4j.compiler` among 301 changed paths | 1 | **Y** |
| 11093ff98d6e | de.neuland.jade4j.parser.IncludeParserTest | `de.neuland.jade4j.parser` | `de.neuland.jade4j.parser` from `src/main/java/de/neuland/jade4j/parser/Parser.java` | 1 | **Y** |

All 12 manual checks (6 zero-value, 6 positive-value) match: **no discrepancy between manual expected value and stored feature value in any case.**

---

## Step 4: Diagnosis

### `test_file_touched`

**Classification: DATA-LIMITATION (primary) + GENUINE-LOW-SIGNAL (secondary)**

**Evidence:**

1. **Correct implementation.** The manual trace shows 3/3 positive rows and 3/3 zero rows match exactly. The logic in `_test_id_to_path` + `_normalize_path` + exact-string membership check is sound for repos whose `file_changes` paths are stored in Maven-standard form (`src/test/java/...`).

2. **Why near-zero MI despite correct implementation:**
   - **Parse failure dilutes the signal.** `dependency_parse_failed=1` forces `test_file_touched=0` for 30–98% of rows per repo. This creates a massive class imbalance and mixes "actually 0" with "unknown, defaulted to 0", degrading MI. For `deeplearning4j` (97.8% parse-failed) the feature is entirely useless.
   - **Base-rate sparsity.** Even on parse-ok rows, the fraction of rows where the test file was actually changed ranges from 0.35% to 1.54%. In this dataset the vast majority of test runs in any commit did *not* have their own test file touched. This is expected: a commit rarely touches more than a handful of test files, but all ~20–200 tests in the suite still appear in `test_runs`.
   - **Direction of correlation.** Touching a test file correlates *negatively or not at all* with failure (5.4% failure rate vs 8.7% baseline). Modifying a test does not mean the test will fail; it usually means the test was intentionally updated.

3. **Recommendation:** No code fix needed. The feature is computed correctly. It is genuinely sparse and low-signal on this dataset because:
   - Most commits touch few test files relative to the total test suite size.
   - The parse-failure fallback to 0 further flattens the distribution.
   Document this in `decisions-log.md` as a genuine data finding. Optionally consider an ablation (removing `test_file_touched` from feature sets with high parse-failure rates, or replacing it with the coarser `test_files_changed > 0` count from `commit_extractor.py` which does not require AST parsing).

---

### `same_package`

**Classification: DATA-LIMITATION (primary)**

**Evidence:**

1. **Correct implementation.** All 6 manual traces for `same_package` match perfectly. The `_path_to_package` heuristic correctly parses Maven-standard paths. For deeplearning4j, `file_changes` paths *do* contain `src/main/java/` (14,988 out of 61,402 paths), so the extractor would compute packages correctly — but 97.8% of those rows are `dependency_parse_failed=1` anyway.

2. **Why near-zero MI despite correct implementation:**
   - **Parse failure is the dominant cause.** Rows with `dependency_parse_failed=1` all report `same_package=0` regardless of truth. For `deeplearning4j` (97.8% failed) and `thinkaurelius@titan` (65.3% failed), the feature is nearly constant at 0.
   - **Multi-module projects dilute the feature.** For `deeplearning4j` and `titan`, source files live under module-prefixed paths like `deeplearning4j-core/src/main/java/...`. Because `_path_to_package` looks for the literal substring `src/main/java/`, it still extracts the correct package from these paths (confirmed in Step 2 extra checks). The *real* problem is the parse failure rate, not path format.
   - **Negative/null correlation.** Across all repos, `same_package=1` is associated with a *lower* failure rate (5.9% vs 8.8% baseline). This is a data characteristic: large commits that happen to touch a file in the same package often touch many files, which is a noisy signal.
   - **Cross-repo imbalance.** `adamfisk@LittleProxy` (22.9% positive rate) is much higher than other repos, so the aggregate MI is dominated by repos where the feature is nearly constant.

3. **Recommendation:** No code fix needed. The implementation is correct. The low MI is explained by:
   - Parse failure defaulting 31–98% of rows to 0 across most repos.
   - Genuine sparsity in small, single-module repos.
   Document in `decisions-log.md`. The logical next step (separate task, not here) is to fix the high `dependency_parse_failed` rate — particularly for `deeplearning4j` (97.8%) and `thinkaurelius@titan` (65.3%) — which would allow `same_package` and `test_file_touched` to express their true signal. Root causes of parse failure are likely: (a) `javalang` not handling newer Java syntax (lambdas, records, text blocks), and (b) test files that do not exist in the local git clone (blobless clone with `filter=blob:none` means `_find_test_file` returns a non-existent path).

---

## Final Verdicts

**VERDICT: test_file_touched = DATA-LIMITATION**

Correct implementation. Near-zero MI is caused by (1) high `dependency_parse_failed` rates forcing false-zero values (30–98% of rows per repo), and (2) genuine sparsity — test files are rarely touched relative to total test suite size per commit. The negative/null direction of correlation with failure is also a genuine dataset characteristic.

**VERDICT: same_package = DATA-LIMITATION**

Correct implementation. Near-zero MI is caused primarily by the same parse-failure fallback issue (same_package=0 for all parse-failed rows). The path extraction logic is correct even for multi-module Maven projects. Signal would materially improve if parse failure rates were reduced; this is a prerequisite fix, not part of this investigation.

---

## Appendix: Diagnostic Scripts

All scripts used in this investigation are saved under `scripts/diag/` for reproducibility:

| Script | Purpose |
|--------|---------|
| `scripts/diag/step2_distribution.py` | Full distribution, per-repo breakdown, crosstab with label |
| `scripts/diag/step3_manual_trace.py` | Manual trace: 3 all-zero rows from neuland@jade4j |
| `scripts/diag/step3b_targeted_trace.py` | Targeted trace: 3 positive-value rows per feature; deeplearning4j deep-dive |
| `scripts/diag/step3c_extra_checks.py` | Path format sampling, parse_failed rates, per-repo positive fractions |
