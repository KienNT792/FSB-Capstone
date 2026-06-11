# P3 — Fix `"SELECTED"` Substring Bug in `load_rtp_dataset.py`

**Priority:** P3  
**Effort estimate:** 15 min  
**Blocking:** Low risk if projects specified manually; blocks reliable `--auto` flag  
**Status:** DONE (verified 2026-06-10 — read_projects_from_summary() line 144 already uses exact column match `cells[4] == "SELECTED"`, not substring check)

---

## Context

`decisions-log.md` Known Drift section:

> *"`data/scripts/load_rtp_dataset.py` currently identifies auto-selected projects by checking whether a summary line contains `"SELECTED"`. Because `"NOT SELECTED"` also contains that substring, verify/fix this before treating an auto-loaded DB as selected-project-only."*

The `--auto` flag reads `data/rtp-project-summary.md` and extracts project names where the Status column contains `"SELECTED"`. Because `"NOT SELECTED"` is a superset of `"SELECTED"`, the current check incorrectly includes **all 20 projects** when `--auto` is used, not just the 5 selected ones.

---

## Tasks

### 1. Locate the bug

Open `data/scripts/load_rtp_dataset.py` and find the section that parses `data/rtp-project-summary.md`. It likely looks like:

```python
if "SELECTED" in line:
    # extract project name
```

### 2. Fix the condition

Change the check to match only exact `SELECTED` status, excluding `NOT SELECTED`:

```python
# Option A: check for exact word boundary
if "| SELECTED |" in line or line.strip().endswith("| SELECTED |"):
    ...

# Option B: parse the Markdown table column properly
parts = [col.strip() for col in line.split("|")]
# parts[0]='' parts[1]=project parts[2]=builds parts[3]=tests parts[4]=fail_rate parts[5]=status
if len(parts) >= 6 and parts[5] == "SELECTED":
    ...

# Option C: use regex
import re
if re.search(r'\|\s*SELECTED\s*\|', line):
    ...
```

Option B (parsing the table column) is the most robust. Use that.

### 3. Add a unit test

In `tests/`, add `test_load_rtp_dataset.py` (or extend existing test file) with a test that mocks a summary file containing both `SELECTED` and `NOT SELECTED` rows and asserts only the correct projects are returned by the auto-detection function.

```python
def test_auto_selection_excludes_not_selected():
    mock_summary = """| Project | Builds | Tests | Failure Rate | Status |
|---------|--------|-------|--------------|--------|
| proj_a@repo | 500 | 10000 | 5.00% | SELECTED |
| proj_b@repo | 300 |  5000 | 0.50% | NOT SELECTED (failure rate < 1%) |
| proj_c@repo | 800 | 20000 | 3.00% | SELECTED |
"""
    # call the auto-detection function with mock content
    selected = parse_selected_projects(mock_summary)
    assert selected == ["proj_a@repo", "proj_c@repo"]
    assert "proj_b@repo" not in selected
```

---

## Verification

```powershell
# Dry run --auto and confirm only 5 projects are detected (not 20)
python data/scripts/load_rtp_dataset.py --auto --dry-run 2>&1 | Select-String "project"
```

If `--dry-run` flag does not exist, add a `--dry-run` flag that prints detected projects without loading.

---

## Done Criteria

- `--auto` flag detects exactly the 5 selected projects (not all 20)
- Unit test for `parse_selected_projects` passes under `pytest tests/`
- No regression in manual `--projects` flag behavior
