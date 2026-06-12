---
# Job 04: DependencyFeatureExtractor

## Objective
Implement `DependencyFeatureExtractor` at `src/features/dependency_extractor.py` with method `extract(test_id: str, changed_java_files: list[str], repo_path: str) -> dict` that returns 4 import-level coupling features between a test file and the files changed in a commit. All `javalang.parse.parse()` failures must be caught silently; the method must never raise on any input.

## Sprint Goal Alignment
This job produces the dependency features (`test_file_touched`, `import_overlap`, `same_package`, `changed_files_in_module`) that capture structural coupling between tests and changed production code. job-05 (FeatureJoiner) calls `extract()` per `(commit, test)` pair, sourcing `changed_java_files` from the `file_changes` DuckDB table (already queried as part of the commit block).

## Dependencies
- Upstream:
  - `data/git-repos/<owner>@<repo>` cloned repos (Sprint 1 deliverable) — needed to read test Java source files on disk
  - `file_changes` table in `data/test_history.db` (sourced by FeatureJoiner before calling this extractor — passed as `changed_java_files` parameter)
- Downstream: job-05 (FeatureJoiner assembles the dependency block), job-09 (unit tests)

## Scope (in)
- Class `DependencyFeatureExtractor` at `src/features/dependency_extractor.py`
- Method `extract(test_id: str, changed_java_files: list[str], repo_path: str) -> dict`
- `test_id` maps to `.java` file path via convention: `com.example.FooTest` → `src/test/java/com/example/FooTest.java`
- `changed_java_files` is a list of file paths from `file_changes` table — no live git diff needed
- Returns 4 features:

| Feature | Type | Description |
|---|---|---|
| `test_file_touched` | int | 1 if the test file itself is in `changed_java_files` |
| `import_overlap` | int | Count of changed files whose class name appears in test file's import list |
| `same_package` | int | 1 if any changed source file shares the test's package |
| `changed_files_in_module` | int | Count of changed files in the same Maven module as the test |

- Fallback when test file cannot be located on disk: return all zeros + `dependency_parse_failed=1`
- `javalang.parse.parse()` failure: catch exception, return zeros + `dependency_parse_failed=1`
- Unit tests use synthetic Java file fixture — no real repo files; ≥ 6 test cases

## Out of Scope
- Querying `file_changes` table directly — FeatureJoiner does this and passes `changed_java_files` as a parameter
- Code churn metrics (`lines_added`, etc.) — job-01
- Author history features — job-02
- Test history rolling statistics — job-03
- Any write to DuckDB or Parquet

## Implementation Notes
**`test_id` to file path mapping:**
- Split on `.`: `com.example.FooTest` → parts `['com', 'example', 'FooTest']`
- Join as `src/test/java/com/example/FooTest.java`
- Prepend `repo_path` to get absolute path
- If file does not exist at that path, set `dependency_parse_failed=1` and return zeros immediately

**`import_overlap` computation:**
- Parse the test file with `javalang.parse.parse(source_text)`
- Extract import declarations from the AST
- For each path in `changed_java_files`, derive the class name: last component of the path without `.java` extension
- Count how many changed class names appear in the test's import list (exact substring match on import path is sufficient)

**`same_package` computation:**
- Extract the test file's package declaration from the AST
- For each path in `changed_java_files`, derive its package: directory path relative to `src/main/java/` or `src/test/java/`, converted to dot notation
- Set `same_package=1` if any changed file's package equals the test's package

**`changed_files_in_module` computation:**
- Maven module = the directory containing the nearest `pom.xml` ancestor
- For each changed file, walk up the path to find the `pom.xml`; count changed files that share the same module root as the test file
- If `pom.xml` detection fails, fall back to: same top-level subdirectory under `repo_path`

**`javalang` is optional/fallible:** per CLAUDE.md and backlog, wrap ALL javalang calls in `try/except`. Parse failures are NOT errors — they are expected at low frequency on Java 8/11 code. Log the failure count per project at pipeline completion (handled by FeatureJoiner's summary line).

**`dependency_parse_failed=1`** must be included in the returned dict even when parsing succeeds (value 0 in normal case).

## Deliverables
- `src/features/dependency_extractor.py`
- `tests/test_dependency_extractor.py` (≥ 6 test cases using synthetic fixture `.java` file)

## Verification
```bash
pytest tests/test_dependency_extractor.py -v
```
≥ 6 cases pass. Parse failure case is tested explicitly (malformed Java source → returns zeros, no exception).

## Definition of Done
- [ ] `DependencyFeatureExtractor` class exists at `src/features/dependency_extractor.py`
- [ ] `extract()` returns dict with 4 features + `dependency_parse_failed` key
- [ ] `test_id` to `.java` file path mapping follows `src/test/java/` convention
- [ ] `changed_java_files` sourced from parameter (no DuckDB query inside this class)
- [ ] File-not-found case returns all zeros + `dependency_parse_failed=1` without raising
- [ ] `javalang.parse.parse()` failure caught silently; returns zeros + `dependency_parse_failed=1`
- [ ] `pytest tests/test_dependency_extractor.py` passes with ≥ 6 test cases using synthetic fixture
- [ ] No test accesses real cloned repos or `data/test_history.db`
---
