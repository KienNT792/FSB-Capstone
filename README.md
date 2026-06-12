# FSB-Capstone

AdaptCI is an ML-based test prioritization project for Java CI pipelines. Sprint 1 uses RTPTorrent CSV data as the ground-truth source; it does not replay Maven builds.

## Repository Layout

```text
data/
  repos/
    rtp-torrent/      # RTPTorrent CSV source dataset
  git-repos/          # local Git clones for commit metadata, generated
  scripts/
    select_rtp_projects.py
    load_rtp_dataset.py
  features/          # generated parquet files
docs/
  backlog/
  plan/
  literature/
notebooks/
src/
tests/
```

## Environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify imports:

```powershell
python -c "import xgboost, lightgbm, mlflow, fastapi, git, javalang, evidently; print('All imports OK')"
```

## Project Selection

Select RTPTorrent projects with enough failure signal:

```powershell
python data/scripts/select_rtp_projects.py --rtp-path data/repos/rtp-torrent
```

The script writes `data/rtp-project-summary.md`.

## DuckDB Load

Load selected projects from the summary:

```powershell
python data/scripts/load_rtp_dataset.py `
  --db-path data/test_history.db `
  --rtp-path data/repos/rtp-torrent `
  --auto `
  --force
```

Manual selection is also supported:

```powershell
python data/scripts/load_rtp_dataset.py `
  --db-path data/test_history.db `
  --rtp-path data/repos/rtp-torrent `
  --projects apache@sling square@okhttp brettwooldridge@HikariCP `
  --force
```

## Timestamp Population

Clone the 5 selected projects under `data/git-repos/<owner>@<repo>`, then populate commit timestamps:

```powershell
python scripts/add_timestamps.py `
  --db-path data/test_history.db `
  --git-root data/git-repos `
  --auto
```

Verify coverage without writing:

```powershell
python scripts/add_timestamps.py `
  --db-path data/test_history.db `
  --git-root data/git-repos `
  --auto `
  --dry-run
```

Expected Sprint 1 handoff status: 5/5 selected projects pass at 100% distinct-SHA timestamp coverage. Rows with `commit_sha IS NULL` remain untimestamped and should use `job_sequence` fallback or be filtered deliberately.

## MLflow

Start local MLflow:

```powershell
docker compose up -d
curl http://localhost:5000/health
```

The UI runs at `http://localhost:5000`.

Stop it with:

```powershell
docker compose down
```

## Generated Artifacts

The following are generated locally and ignored by git:

- `data/repos/rtp-torrent/`
- `data/git-repos/`
- `data/features/`
- `data/test_history.db` (DuckDB database file)
- `mlflow-artifacts/`
- `mlflow-db/`

## Sprint 1 Reference

Use `docs/reports/sprint-1-completion-report.md` and `data/rtp-project-summary.md` as the Sprint 2 data baseline. `scripts/data_pipeline.py` is still a placeholder and must be implemented before feature artifacts can be generated.
