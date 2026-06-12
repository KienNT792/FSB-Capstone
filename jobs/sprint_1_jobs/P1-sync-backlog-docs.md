# P1 — Sync Backlog Documentation to ADR

**Priority:** P1  
**Effort estimate:** 30 min  
**Blocking:** Unblocks clear Definition of Done for Sprint 1  
**Status:** TODO

---

## Context

`decisions-log.md` (2026-05-10) records an ADR lowering the project selection threshold from `>= 2%` to `>= 1%` and expanding the selected set from 3 to 5 projects. The code (`select_rtp_projects.py`) and validation notebook already implement this decision correctly. However, the following documents still contain stale text that contradicts the ADR:

- `docs/backlog/sprint-1-backlog.md` — DoD still says `>= 2%` and lists exactly 3 projects
- `docs/backlog/sprint-2-backlog.md` — callout block says "Only 3 of 20 RTPTorrent projects meet selection criteria (failure rate ≥ 2%)" and names only deeplearning4j, wicket-bootstrap, jade4j

**Do NOT change the code or the notebook.** Only update the documentation.

---

## Tasks

### 1. Update `docs/backlog/sprint-1-backlog.md`

In the **Definition of Done** section, update:

- Change: `Exactly 3 RTPTorrent projects confirmed and documented: deeplearning4j@deeplearning4j, l0rdn1kk0n@wicket-bootstrap, neuland@jade4j`
- To: `Exactly 5 RTPTorrent projects confirmed and documented (failure rate ≥ 1%, builds ≥ 100, has -patches.csv): deeplearning4j@deeplearning4j (6.0%), l0rdn1kk0n@wicket-bootstrap (20.5%), neuland@jade4j (3.7%), adamfisk@LittleProxy (1.2%), thinkaurelius@titan (1.5%)`

- Change: `Failure ratio documented per selected project (imbalance report)` — add note: `LittleProxy and titan have failure rate < 2%; all results on these two projects must include a low-failure-rate/high-variance caveat in thesis.`

In the **S1-03 story** section, update the selection criteria bullet:
- Change `Failure rate ≥ 2%` to `Failure rate ≥ 1%`
- Update the "Verified selection results" table to include all 5 selected projects

### 2. Update `docs/backlog/sprint-2-backlog.md`

Replace the stale callout block (lines starting with `> **Project selection update:**`) with:

```
> **Project selection update (ADR 2026-05-10):** The selection threshold was lowered from `>= 2%` to `>= 1%` to ensure sufficient project diversity for the thesis. Five projects are selected: `deeplearning4j@deeplearning4j` (6.0%), `l0rdn1kk0n@wicket-bootstrap` (20.5%), `neuland@jade4j` (3.7%), `adamfisk@LittleProxy` (1.2%), `thinkaurelius@titan` (1.5%). S2/S3 scripts must target all 5 projects. Results on LittleProxy and titan must include explicit low-failure-rate caveats. See `decisions-log.md` (2026-05-10) for rationale.
```

Also update the **Definition of Done** in sprint-2-backlog.md:
- Change `timestamp populated for ≥ 70% of commits across all 3 selected projects` → `all 5 selected projects`
- Change `python scripts/data_pipeline.py --project deeplearning4j@deeplearning4j` produces `full_features.parquet` → note that all 5 projects must be runnable

### 3. Update `CLAUDE.md`

In the **Current State** section, the line `Exactly 3 RTPTorrent projects confirmed...` (if present) should reflect 5 projects.

---

## Verification

After edits, grep for `>= 2%` and `3 projects` in backlog files to confirm no stale text remains:

```powershell
Select-String -Path "docs\backlog\sprint-1-backlog.md","docs\backlog\sprint-2-backlog.md" -Pattern ">= 2%" 
Select-String -Path "docs\backlog\sprint-1-backlog.md","docs\backlog\sprint-2-backlog.md" -Pattern "Only 3"
```

---

## Done Criteria

- Both backlog files reflect `>= 1%` threshold and 5 selected projects
- No remaining references to "only 3 projects" or ">= 2%" selection criteria in sprint-1 or sprint-2 backlogs
- `decisions-log.md` is unchanged
- Code and notebook are unchanged
