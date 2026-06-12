---
# Job 06: End-to-End data_pipeline.py

## Objective
Create `scripts/data_pipeline.py` — the single CLI command that takes a project name and runs the full feature extraction pipeline end-to-end, producing `{repo}_features.parquet` in ≤ 5 minutes. The script calls `FeatureJoiner.build()` (job-05) and then `validate_features()` (job-07) in sequence, then prints a summary line and exits 0.

## Sprint Goal Alignment
This script IS the sprint goal deliverable: `python scripts/data_pipeline.py --project <name>` is the "single command" the sprint Definition of Done requires. All other jobs build components that this script wires together.

## Dependencies
- Upstream:
  - job-05: `FeatureJoiner` must exist and be importable
  - job-07: `validate_features()` must exist (called at end of pipeline)
  - `data/test_history.db` populated (Sprint 1)
  - Git repos cloned under `data/git-repos/` (Sprint 1)
- Downstream: job-07 (validation is called from here), job-08 (EDA notebook loads the Parquet this produces)

## Scope (in)
- Script at `scripts/data_pipeline.py`
- CLI interface: `python scripts/data_pipeline.py --project <user>@<project> --db-path PATH --rtp-path PATH --output-path PATH`
  - `--project`: required; RTPTorrent project identifier (e.g. `neuland@jade4j`)
  - `--db-path`: default `data/test_history.db`
  - `--rtp-path`: default `data/repos/rtp-torrent`
  - `--output-path`: default `data/features/{project}_features.parquet`
- Execution sequence:
  1. Parse args
  2. Instantiate `FeatureJoiner`
  3. Call `FeatureJoiner.build(repo, db_path)` → returns DataFrame
  4. Call `validate_features(df)` → raises `AssertionError` on failure
  5. Save DataFrame to output Parquet path
  6. Print summary line
- Final summary line format: `"Done. Shape: (N rows, M cols). Label distribution: {0: X, 1: Y}. commit_meta_missing: Z rows."`
- Idempotent: if output Parquet already exists AND `--force` flag is NOT set → print `"Output exists. Use --force to overwrite."` and exit 0
- Runtime: ≤ 5 minutes for a single project on standard laptop hardware

## Out of Scope
- Model training, hyperparameter tuning — Sprint 3+
- Running across all 5 projects in one command — this script takes one `--project` at a time; a wrapper loop (if needed) is separate
- Modifying `test_history.db` — read-only access only
- EDA — job-08

## Implementation Notes
**Imports needed:** `argparse`, `pathlib.Path`, `src.features.feature_joiner.FeatureJoiner`, `src.features.validation.validate_features`

**`--output-path` default derivation:**
```python
default = f"data/features/{args.project}_features.parquet"
```

**Idempotency check:**
```python
if Path(args.output_path).exists() and not args.force:
    print("Output exists. Use --force to overwrite.")
    sys.exit(0)
```

**`commit_meta_missing` count** for the summary line: after `build()` returns, compute `df['commit_meta_missing'].sum()` before saving to Parquet.

**Error handling:** let `AssertionError` from `validate_features()` propagate uncaught — this gives a visible stack trace pointing to the failing assertion. Do not wrap in a try/except that swallows the message.

**Performance:** if ≥ 5 minutes is exceeded for any project other than deeplearning4j (which has 61,402 `file_changes` rows), investigate commit-batching in FeatureJoiner before optimizing here. The script itself should not contain performance logic — it is a thin wrapper.

**No unit test for this script** — it is an integration entrypoint. The Milestone M1 Checklist command in the backlog is the acceptance test.

## Deliverables
- `scripts/data_pipeline.py`

## Verification
```bash
# Idempotency check
python scripts/data_pipeline.py --project neuland@jade4j
python scripts/data_pipeline.py --project neuland@jade4j
# Second run must print: "Output exists. Use --force to overwrite." and exit 0

# Full run with --force
python scripts/data_pipeline.py --project neuland@jade4j --force
# Expected output ends with: "Done. Shape: (N rows, M cols). Label distribution: {0: X, 1: Y}. commit_meta_missing: Z rows."
# Expected runtime: ≤ 5 minutes

# Milestone M1 command (exact, from backlog)
python scripts/data_pipeline.py \
  --project neuland@jade4j \
  --db-path data/test_history.db \
  --rtp-path data/repos/rtp-torrent \
  --output-path data/features/neuland@jade4j_features.parquet
```

## Definition of Done
- [ ] `scripts/data_pipeline.py` exists and is runnable
- [ ] CLI accepts `--project`, `--db-path`, `--rtp-path`, `--output-path`, `--force`
- [ ] Calls `FeatureJoiner.build()` then `validate_features()` in sequence
- [ ] Idempotent: second run without `--force` prints correct message and exits 0
- [ ] Final summary line printed in specified format
- [ ] Completes in ≤ 5 minutes for `neuland@jade4j` (baseline project)
- [ ] Milestone M1 command runs without errors; output shape ≥ (5000, 20)
---
