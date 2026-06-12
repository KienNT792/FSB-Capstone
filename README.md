# FSB-Capstone

AdaptCI is an ML-based test prioritization project for Java CI pipelines. Sprint 1 uses RTPTorrent CSV data as the ground-truth source; it does not replay Maven builds.

## Repository Layout

```text
data/
  repos/
    rtp-torrent/      # RTPTorrent CSV source dataset
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
python -m venv .venv
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
- `data/features/`
- `data/test_history.db` (DuckDB database file)
- `mlflow-artifacts/`
- `mlflow-db/`
