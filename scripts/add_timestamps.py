#!/usr/bin/env python3
"""
Populate test_runs.timestamp from local Git commit metadata.

Timestamps are resolved at commit level from GitPython's committed_date value.
Rows without commit_sha, missing local repositories, or SHAs not present in the
local clone remain NULL and can still use job_sequence as temporal fallback.
"""

from __future__ import annotations

import argparse
import os
import sys

import duckdb
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SUMMARY_PATH = Path("data/rtp-project-summary.md")
DEFAULT_MIN_COVERAGE = 70.0


@dataclass(frozen=True)
class CommitGroup:
    commit_sha: str
    row_count: int
    timestamped_rows: int


@dataclass(frozen=True)
class ProjectTimestampReport:
    project: str
    total_shas: int
    resolved_shas: int
    eligible_rows: int
    timestamped_rows: int
    missing_repo: int = 0
    sha_not_found: int = 0
    git_error: int = 0

    @property
    def sha_coverage_pct(self) -> float:
        if self.total_shas == 0:
            return 0.0
        return 100.0 * self.resolved_shas / self.total_shas

    @property
    def row_coverage_pct(self) -> float:
        if self.eligible_rows == 0:
            return 0.0
        return 100.0 * self.timestamped_rows / self.eligible_rows

    def passes(self, min_sha_coverage: float, min_row_coverage: float) -> bool:
        return (
            self.sha_coverage_pct >= min_sha_coverage
            and self.row_coverage_pct >= min_row_coverage
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate DuckDB test_runs.timestamp from local Git clones."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        required=True,
        help="DuckDB database containing the test_runs table.",
    )
    parser.add_argument(
        "--git-root",
        type=Path,
        required=True,
        help="Root containing cloned repos named <owner>@<repo>.",
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        default=[],
        help="Selected owner@project names. Supports spaces or commas.",
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
        "--min-sha-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help="Minimum resolved distinct-SHA coverage required outside dry-run.",
    )
    parser.add_argument(
        "--min-row-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help="Minimum timestamped row coverage required outside dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report resolvability without updating DuckDB.",
    )
    return parser.parse_args()


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
        if len(cells) >= 5 and cells[0] != "Project" and cells[4] == "SELECTED":
            projects.append(cells[0])
    return projects


def resolve_projects(args: argparse.Namespace) -> list[str]:
    projects = normalize_projects(args.projects)
    if args.auto:
        projects.extend(read_projects_from_summary(args.summary_path))

    deduped: list[str] = []
    seen: set[str] = set()
    for project in projects:
        if project not in seen:
            seen.add(project)
            deduped.append(project)

    if not deduped:
        raise ValueError("Provide --projects or use --auto with a selected summary.")
    return deduped


def validate_schema(connection: duckdb.DuckDBPyConnection) -> None:
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'test_runs';"
    ).fetchall()
    if not rows:
        raise ValueError("DuckDB table not found: test_runs")

    columns = {row[0] for row in rows}
    required = {"repo", "commit_sha", "timestamp"}
    missing = sorted(required - columns)
    if missing:
        raise ValueError(
            "test_runs is missing required column(s): " + ", ".join(missing)
        )


def fetch_commit_groups(
    connection: duckdb.DuckDBPyConnection,
    project: str,
) -> list[CommitGroup]:
    rows = connection.execute(
        """
        SELECT
            commit_sha,
            COUNT(*) AS row_count,
            SUM(CASE WHEN timestamp IS NOT NULL THEN 1 ELSE 0 END)
                AS timestamped_rows
        FROM test_runs
        WHERE repo = ?
          AND commit_sha IS NOT NULL
          AND TRIM(commit_sha) != ''
        GROUP BY commit_sha
        ORDER BY commit_sha;
        """,
        (project,),
    ).fetchall()
    return [
        CommitGroup(
            commit_sha=str(commit_sha),
            row_count=int(row_count),
            timestamped_rows=int(timestamped_rows or 0),
        )
        for commit_sha, row_count, timestamped_rows in rows
    ]


def create_git_repo(repo_path: Path):
    from git import Repo

    add_process_safe_directory(repo_path)
    return Repo(repo_path)


def add_process_safe_directory(repo_path: Path) -> None:
    """Trust a local clone for this process without writing global git config."""
    safe_path = repo_path.resolve().as_posix()
    existing_count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    for index in range(existing_count):
        key = os.environ.get(f"GIT_CONFIG_KEY_{index}")
        value = os.environ.get(f"GIT_CONFIG_VALUE_{index}")
        if key == "safe.directory" and value == safe_path:
            return

    os.environ["GIT_CONFIG_COUNT"] = str(existing_count + 1)
    os.environ[f"GIT_CONFIG_KEY_{existing_count}"] = "safe.directory"
    os.environ[f"GIT_CONFIG_VALUE_{existing_count}"] = safe_path


def is_sha_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        exc.__class__.__name__ in {"BadName", "BadObject"}
        or "could not be resolved" in message
        or " missing" in message
    )


def update_timestamp(
    connection: duckdb.DuckDBPyConnection,
    project: str,
    commit_sha: str,
    timestamp: int,
) -> None:
    connection.execute(
        """
        UPDATE test_runs
        SET timestamp = ?
        WHERE repo = ?
          AND commit_sha = ?
          AND timestamp IS NULL;
        """,
        (timestamp, project, commit_sha),
    )


def resolve_project_timestamps(
    connection: duckdb.DuckDBPyConnection,
    project: str,
    git_root: Path,
    dry_run: bool,
) -> ProjectTimestampReport:
    groups = fetch_commit_groups(connection, project)
    eligible_rows = sum(group.row_count for group in groups)
    timestamped_rows = sum(group.timestamped_rows for group in groups)
    resolved_shas = sum(
        1 for group in groups if group.timestamped_rows == group.row_count
    )
    unresolved_groups = [
        group for group in groups if group.timestamped_rows < group.row_count
    ]

    if not unresolved_groups:
        return ProjectTimestampReport(
            project=project,
            total_shas=len(groups),
            resolved_shas=resolved_shas,
            eligible_rows=eligible_rows,
            timestamped_rows=timestamped_rows,
        )

    repo_path = git_root / project
    if not repo_path.exists():
        return ProjectTimestampReport(
            project=project,
            total_shas=len(groups),
            resolved_shas=resolved_shas,
            eligible_rows=eligible_rows,
            timestamped_rows=timestamped_rows,
            missing_repo=len(unresolved_groups),
        )

    try:
        git_repo = create_git_repo(repo_path)
    except Exception:
        return ProjectTimestampReport(
            project=project,
            total_shas=len(groups),
            resolved_shas=resolved_shas,
            eligible_rows=eligible_rows,
            timestamped_rows=timestamped_rows,
            git_error=len(unresolved_groups),
        )

    sha_not_found = 0
    git_error = 0
    for group in unresolved_groups:
        try:
            timestamp = int(git_repo.commit(group.commit_sha).committed_date)
        except Exception as exc:
            if is_sha_not_found_error(exc):
                sha_not_found += 1
            else:
                git_error += 1
            continue

        resolved_shas += 1
        timestamped_rows += group.row_count - group.timestamped_rows
        if not dry_run:
            update_timestamp(connection, project, group.commit_sha, timestamp)

    if not dry_run:
        connection.commit()

    return ProjectTimestampReport(
        project=project,
        total_shas=len(groups),
        resolved_shas=resolved_shas,
        eligible_rows=eligible_rows,
        timestamped_rows=timestamped_rows,
        sha_not_found=sha_not_found,
        git_error=git_error,
    )


def print_report(
    report: ProjectTimestampReport,
    min_sha_coverage: float,
    min_row_coverage: float,
    dry_run: bool,
) -> None:
    mode = "DRY-RUN " if dry_run else ""
    status = "PASS" if report.passes(min_sha_coverage, min_row_coverage) else "FAIL"
    print(
        f"{mode}{report.project}: "
        f"{report.resolved_shas}/{report.total_shas} SHAs "
        f"({report.sha_coverage_pct:.1f}%), "
        f"{report.timestamped_rows}/{report.eligible_rows} rows "
        f"({report.row_coverage_pct:.1f}%) [{status}]"
    )
    print(
        "unresolved: "
        f"missing_repo={report.missing_repo}, "
        f"sha_not_found={report.sha_not_found}, "
        f"git_error={report.git_error}"
    )


def main() -> int:
    args = parse_args()
    require_path(args.db_path, "DuckDB database")
    require_path(args.git_root, "Git clone root")
    projects = resolve_projects(args)

    connection = duckdb.connect(str(args.db_path))
    try:
        validate_schema(connection)
        reports = [
            resolve_project_timestamps(
                connection=connection,
                project=project,
                git_root=args.git_root,
                dry_run=args.dry_run,
            )
            for project in projects
        ]
    finally:
        connection.close()

    for report in reports:
        print_report(
            report,
            min_sha_coverage=args.min_sha_coverage,
            min_row_coverage=args.min_row_coverage,
            dry_run=args.dry_run,
        )

    if args.dry_run:
        return 0

    failed = [
        report
        for report in reports
        if not report.passes(args.min_sha_coverage, args.min_row_coverage)
    ]
    if failed:
        print(
            "Timestamp coverage gate failed for: "
            + ", ".join(report.project for report in failed),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
