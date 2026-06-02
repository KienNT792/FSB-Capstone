#!/usr/bin/env python3
"""
Load selected RTPTorrent CSV data into SQLite.

Usage:
    python scripts/load_rtp_dataset.py --db-path data/test_history.db \
        --rtp-path data/repos/rtp-torrent --auto

    python scripts/load_rtp_dataset.py --db-path data/test_history.db \
        --rtp-path data/repos/rtp-torrent \
        --projects apache@sling square@okhttp brettwooldridge@HikariCP
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SUMMARY_PATH = Path("data/rtp-project-summary.md")
MAIN_COLUMNS = {
    "travisJobId",
    "testName",
    "index",
    "duration",
    "count",
    "failures",
    "errors",
    "skipped",
}
BATCH_SIZE = 10_000


@dataclass(frozen=True)
class ProjectLoadResult:
    project: str
    test_runs_inserted: int
    file_changes_inserted: int
    test_rows_seen: int
    unmapped_rows: int
    null_duration_rows: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load RTPTorrent project CSVs into SQLite."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        required=True,
        help="SQLite database path to create or append to.",
    )
    parser.add_argument(
        "--rtp-path",
        type=Path,
        required=True,
        help="RTPTorrent data root.",
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        default=[],
        help=(
            "Selected owner@project names. Supports space-separated values "
            "or comma-separated values."
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=f"Read selected projects from {DEFAULT_SUMMARY_PATH}.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help=f"Project summary used with --auto. Default: {DEFAULT_SUMMARY_PATH}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop and recreate tables before loading.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read inputs and print counts without writing to SQLite.",
    )
    return parser.parse_args()


def clean_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_int(value: object) -> int:
    text = clean_text(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def read_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def normalize_projects(project_args: Iterable[str]) -> list[str]:
    projects: list[str] = []
    for item in project_args:
        for part in item.split(","):
            project = part.strip()
            if project:
                projects.append(project)
    return projects


def read_projects_from_summary(summary_path: Path) -> list[str]:
    require_path(summary_path, "Project summary")
    projects: list[str] = []
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "SELECTED" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 5 and cells[0] != "Project":
            projects.append(cells[0])
    return projects


def resolve_projects(args: argparse.Namespace) -> list[str]:
    projects = normalize_projects(args.projects)
    if args.auto:
        auto_projects = read_projects_from_summary(args.summary_path)
        projects.extend(auto_projects)

    deduped: list[str] = []
    seen: set[str] = set()
    for project in projects:
        if project not in seen:
            seen.add(project)
            deduped.append(project)

    if not deduped:
        raise ValueError("Provide --projects or use --auto with a selected summary.")
    return deduped


def find_main_csv(project_dir: Path) -> Path | None:
    exact = project_dir / f"{project_dir.name}.csv"
    if exact.exists():
        return exact

    candidates = []
    for csv_path in project_dir.glob("*.csv"):
        name = csv_path.name
        if name.endswith(("-patches.csv", "-pr.csv", "-offenders.csv")):
            continue
        candidates.append(csv_path)

    for csv_path in sorted(candidates):
        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.reader(handle)
                header = set(next(reader, []))
        except OSError:
            continue
        if MAIN_COLUMNS.issubset(header):
            return csv_path
    return None


def find_patches_csv(project_dir: Path) -> Path | None:
    exact = project_dir / f"{project_dir.name}-patches.csv"
    if exact.exists():
        return exact

    candidates = sorted(project_dir.glob("*-patches.csv"))
    return candidates[0] if candidates else None


def load_commit_mapping(mapping_path: Path) -> dict[str, str]:
    require_path(mapping_path, "Mapping file")
    mapping: dict[str, str] = {}
    with mapping_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if "tr_job_id" not in fieldnames:
            raise ValueError(f"{mapping_path} is missing required column: tr_job_id")
        sha_column = "git_commit_id" if "git_commit_id" in fieldnames else "sha"
        if sha_column not in fieldnames:
            raise ValueError(
                f"{mapping_path} is missing required commit column: git_commit_id"
            )

        for row in reader:
            job_id = clean_text(row.get("tr_job_id"))
            commit_sha = clean_text(row.get(sha_column))
            if job_id and commit_sha:
                mapping[job_id] = commit_sha
    return mapping


def connect_database(db_path: Path, force: bool) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    if force:
        connection.executescript(
            """
            DROP TABLE IF EXISTS test_runs;
            DROP TABLE IF EXISTS file_changes;
            """
        )
    create_schema(connection)
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS test_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            repo            TEXT NOT NULL,
            job_id          TEXT NOT NULL,
            commit_sha      TEXT,
            test_id         TEXT NOT NULL,
            test_index      INTEGER,
            outcome         TEXT NOT NULL,
            duration_ms     REAL,
            timestamp       INTEGER,
            job_sequence    INTEGER,
            run_count       INTEGER,
            UNIQUE(repo, job_id, test_id)
        );

        CREATE TABLE IF NOT EXISTS file_changes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            repo            TEXT NOT NULL,
            commit_sha      TEXT NOT NULL,
            file_path       TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_test_runs_commit ON test_runs(commit_sha);
        CREATE INDEX IF NOT EXISTS idx_test_runs_test_id ON test_runs(test_id);
        CREATE INDEX IF NOT EXISTS idx_test_runs_job_seq ON test_runs(repo, job_sequence);
        CREATE INDEX IF NOT EXISTS idx_file_changes_commit ON file_changes(commit_sha);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_file_changes_unique
            ON file_changes(repo, commit_sha, file_path);
        """
    )


def derive_outcome(failures: int, errors: int, skipped: int, run_count: int) -> str:
    if failures > 0 or errors > 0:
        return "FAIL"
    if skipped > 0 and skipped == run_count:
        return "SKIPPED"
    return "PASS"


def insert_test_batch(
    connection: sqlite3.Connection,
    rows: list[tuple[object, ...]],
) -> int:
    before = connection.total_changes
    connection.executemany(
        """
        INSERT OR IGNORE INTO test_runs (
            repo,
            job_id,
            commit_sha,
            test_id,
            test_index,
            outcome,
            duration_ms,
            timestamp,
            job_sequence,
            run_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    connection.commit()
    return connection.total_changes - before


def populate_job_sequence(connection: sqlite3.Connection, project: str) -> None:
    """Assign job_sequence as a dense rank over numeric job_id within a project.

    job_sequence is the fallback temporal ordering for Sprint 2 temporal_split
    when timestamp is NULL. TravisCI job IDs are monotonically increasing integers,
    so their numeric order reliably reflects build sequence.
    """
    rows = connection.execute(
        "SELECT DISTINCT job_id FROM test_runs WHERE repo = ?", (project,)
    ).fetchall()
    sorted_job_ids = sorted(rows, key=lambda r: int(r[0]) if r[0].isdigit() else 0)
    for seq, (job_id,) in enumerate(sorted_job_ids, start=1):
        connection.execute(
            "UPDATE test_runs SET job_sequence = ? WHERE repo = ? AND job_id = ?",
            (seq, project, job_id),
        )
    connection.commit()


def insert_file_batch(
    connection: sqlite3.Connection,
    rows: list[tuple[str, str, str]],
) -> int:
    before = connection.total_changes
    connection.executemany(
        """
        INSERT OR IGNORE INTO file_changes (repo, commit_sha, file_path)
        VALUES (?, ?, ?);
        """,
        rows,
    )
    connection.commit()
    return connection.total_changes - before


def count_main_rows(
    main_csv: Path,
    mapping: dict[str, str],
) -> tuple[int, int, int]:
    rows_seen = 0
    unmapped = 0
    null_duration = 0
    with main_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = MAIN_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{main_csv} is missing required columns: {missing}")

        for row in reader:
            rows_seen += 1
            job_id = clean_text(row.get("travisJobId"))
            if not mapping.get(job_id):
                unmapped += 1
            if read_float(row.get("duration")) is None:
                null_duration += 1
    return rows_seen, unmapped, null_duration


def count_patch_rows(patches_csv: Path) -> int:
    rows_seen = 0
    with patches_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if clean_text(row.get("sha")) and clean_text(row.get("name")):
                rows_seen += 1
    return rows_seen


def load_test_runs(
    connection: sqlite3.Connection,
    project: str,
    main_csv: Path,
    mapping: dict[str, str],
) -> tuple[int, int, int, int]:
    inserted = 0
    rows_seen = 0
    unmapped = 0
    null_duration = 0
    batch: list[tuple[object, ...]] = []

    with main_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = MAIN_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{main_csv} is missing required columns: {missing}")

        for row in reader:
            rows_seen += 1
            job_id = clean_text(row.get("travisJobId"))
            commit_sha = mapping.get(job_id)
            if commit_sha is None:
                unmapped += 1

            run_count = read_int(row.get("count"))
            failures = read_int(row.get("failures"))
            errors = read_int(row.get("errors"))
            skipped = read_int(row.get("skipped"))
            duration = read_float(row.get("duration"))
            duration_ms = duration * 1000 if duration is not None else None
            if duration_ms is None:
                null_duration += 1

            # timestamp is NULL at load time; populated separately via --add-timestamps
            # job_sequence is set after all rows are inserted (see populate_job_sequence)
            batch.append(
                (
                    project,
                    job_id,
                    commit_sha,
                    clean_text(row.get("testName")),
                    read_int(row.get("index")),
                    derive_outcome(failures, errors, skipped, run_count),
                    duration_ms,
                    None,  # timestamp
                    None,  # job_sequence — populated post-insert
                    run_count,
                )
            )

            if len(batch) >= BATCH_SIZE:
                inserted += insert_test_batch(connection, batch)
                batch.clear()

    if batch:
        inserted += insert_test_batch(connection, batch)
    return inserted, rows_seen, unmapped, null_duration


def load_file_changes(
    connection: sqlite3.Connection,
    project: str,
    patches_csv: Path,
) -> int:
    inserted = 0
    batch: list[tuple[str, str, str]] = []

    with patches_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            commit_sha = clean_text(row.get("sha"))
            file_path = clean_text(row.get("name"))
            if not commit_sha or not file_path:
                continue

            batch.append((project, commit_sha, file_path))
            if len(batch) >= BATCH_SIZE:
                inserted += insert_file_batch(connection, batch)
                batch.clear()

    if batch:
        inserted += insert_file_batch(connection, batch)
    return inserted


def load_project(
    connection: sqlite3.Connection | None,
    rtp_path: Path,
    project: str,
    mapping: dict[str, str],
    dry_run: bool,
) -> ProjectLoadResult:
    project_dir = rtp_path / project
    require_path(project_dir, f"Project directory for {project}")

    main_csv = find_main_csv(project_dir)
    if main_csv is None:
        raise FileNotFoundError(f"No main CSV found for {project}")

    patches_csv = find_patches_csv(project_dir)
    if patches_csv is None:
        raise FileNotFoundError(f"No patches CSV found for {project}")

    if dry_run:
        rows_seen, unmapped, null_duration = count_main_rows(main_csv, mapping)
        patch_rows = count_patch_rows(patches_csv)
        return ProjectLoadResult(project, rows_seen, patch_rows, rows_seen, unmapped, null_duration)

    if connection is None:
        raise ValueError("Database connection is required outside dry-run mode.")

    test_runs_inserted, rows_seen, unmapped, null_duration = load_test_runs(
        connection, project, main_csv, mapping
    )
    populate_job_sequence(connection, project)
    file_changes_inserted = load_file_changes(connection, project, patches_csv)
    return ProjectLoadResult(
        project=project,
        test_runs_inserted=test_runs_inserted,
        file_changes_inserted=file_changes_inserted,
        test_rows_seen=rows_seen,
        unmapped_rows=unmapped,
        null_duration_rows=null_duration,
    )


def main() -> int:
    args = parse_args()
    require_path(args.rtp_path, "RTPTorrent root")
    projects = resolve_projects(args)

    mapping_path = args.rtp_path / "tr_all_built_commits.csv"
    print(f"Loading mapping from {mapping_path}...")
    mapping = load_commit_mapping(mapping_path)
    print(f"Loaded {len(mapping)} job-to-commit mappings.")

    connection = None
    if not args.dry_run:
        connection = connect_database(args.db_path, args.force)

    results: list[ProjectLoadResult] = []
    failures: list[tuple[str, Exception]] = []
    try:
        for project in projects:
            try:
                result = load_project(
                    connection=connection,
                    rtp_path=args.rtp_path,
                    project=project,
                    mapping=mapping,
                    dry_run=args.dry_run,
                )
                results.append(result)
                verb = "would insert" if args.dry_run else "inserted"
                print(
                    f"{project}: {verb} {result.test_runs_inserted} test_runs, "
                    f"{result.file_changes_inserted} file_changes"
                )
            except Exception as exc:
                failures.append((project, exc))
                print(f"{project}: failed: {exc}", file=sys.stderr)
    finally:
        if connection is not None:
            connection.close()

    if not results:
        details = "; ".join(f"{project}: {exc}" for project, exc in failures)
        raise RuntimeError(f"All projects failed to load. {details}")

    total_test_runs = sum(result.test_runs_inserted for result in results)
    total_file_changes = sum(result.file_changes_inserted for result in results)
    total_rows_seen = sum(result.test_rows_seen for result in results)
    total_unmapped = sum(result.unmapped_rows for result in results)
    total_null_dur = sum(result.null_duration_rows for result in results)
    unmapped_rate = total_unmapped / total_rows_seen if total_rows_seen else 0.0
    null_dur_rate = total_null_dur / total_rows_seen if total_rows_seen else 0.0
    suffix = " (dry run)" if args.dry_run else ""

    print(
        f"Done{suffix}. Total: {total_test_runs} test_runs, "
        f"{total_file_changes} file_changes in {len(results)} projects."
    )
    print(f"SHA unmapped:    {total_unmapped} rows ({unmapped_rate:.2%}).")
    print(f"duration_ms NULL: {total_null_dur} rows ({null_dur_rate:.2%}).")
    if null_dur_rate > 0.10:
        print(
            "WARNING: > 10% of rows have null duration_ms. "
            "avg_duration_ms features in Sprint 2 will be unreliable for these projects."
        )
    print(
        "NOTE: timestamp=NULL for all rows. "
        "Run with --add-timestamps after S1-03 repos are cloned to populate git commit dates. "
        "job_sequence is available now as temporal ordering fallback."
    )

    if failures:
        print(f"Skipped {len(failures)} failed project(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
