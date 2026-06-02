#!/usr/bin/env python3
"""
Select RTPTorrent projects for model training.

Usage:
    python scripts/select_rtp_projects.py
    python scripts/select_rtp_projects.py --rtp-path data/repos/rtp-torrent
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RTP_PATH = Path("data/repos/rtp-torrent")
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


@dataclass(frozen=True)
class ProjectStats:
    project: str
    build_count: int
    test_count: int
    failure_rate: float
    patch_file_exists: bool
    qualifies: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select RTPTorrent projects with enough failure signal."
    )
    parser.add_argument(
        "--rtp-path",
        type=Path,
        default=DEFAULT_RTP_PATH,
        help=f"RTPTorrent data root. Default: {DEFAULT_RTP_PATH}",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help=f"Markdown summary output. Default: {DEFAULT_SUMMARY_PATH}",
    )
    parser.add_argument(
        "--failure-rate-threshold",
        type=float,
        default=0.02,
        help="Minimum aggregated failure rate. Default: 0.02",
    )
    parser.add_argument(
        "--min-builds",
        type=int,
        default=100,
        help="Minimum distinct mapped Travis job IDs. Default: 100",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum projects to select. Default: 5",
    )
    parser.add_argument(
        "--min-selected",
        type=int,
        default=3,
        help="Minimum qualified projects required. Default: 3",
    )
    return parser.parse_args()


def require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def read_mapping_job_ids(mapping_path: Path) -> set[str]:
    require_path(mapping_path, "Mapping file")
    job_ids: set[str] = set()
    with mapping_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if "tr_job_id" not in (reader.fieldnames or []):
            raise ValueError(f"{mapping_path} is missing required column: tr_job_id")
        for row in reader:
            job_id = clean_text(row.get("tr_job_id"))
            if job_id:
                job_ids.add(job_id)
    return job_ids


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


def iter_project_dirs(rtp_path: Path) -> list[Path]:
    require_path(rtp_path, "RTPTorrent root")
    return sorted(
        path
        for path in rtp_path.iterdir()
        if path.is_dir() and "@" in path.name and find_main_csv(path) is not None
    )


def analyze_project(
    project_dir: Path,
    mapping_job_ids: set[str],
    failure_rate_threshold: float,
    min_builds: int,
) -> ProjectStats:
    main_csv = find_main_csv(project_dir)
    if main_csv is None:
        raise FileNotFoundError(f"No main CSV found for {project_dir.name}")

    test_count = 0
    total_runs = 0
    total_failures = 0
    total_errors = 0
    mapped_build_ids: set[str] = set()

    with main_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = MAIN_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{main_csv} is missing required columns: {missing}")

        for row in reader:
            test_count += 1
            total_runs += read_int(row.get("count"))
            total_failures += read_int(row.get("failures"))
            total_errors += read_int(row.get("errors"))

            job_id = clean_text(row.get("travisJobId"))
            if job_id in mapping_job_ids:
                mapped_build_ids.add(job_id)

    failure_rate = (
        (total_failures + total_errors) / total_runs if total_runs > 0 else 0.0
    )
    patch_file_exists = find_patches_csv(project_dir) is not None
    build_count = len(mapped_build_ids)
    qualifies = (
        failure_rate >= failure_rate_threshold
        and build_count >= min_builds
        and patch_file_exists
    )

    return ProjectStats(
        project=project_dir.name,
        build_count=build_count,
        test_count=test_count,
        failure_rate=failure_rate,
        patch_file_exists=patch_file_exists,
        qualifies=qualifies,
    )


def status_for(
    stats: ProjectStats,
    selected_projects: set[str],
    min_builds: int,
    failure_rate_threshold: float,
) -> str:
    if stats.project in selected_projects:
        return "SELECTED"
    if stats.qualifies:
        return "QUALIFIED"
    reasons = []
    if not stats.patch_file_exists:
        reasons.append("no patches")
    if stats.build_count < min_builds:
        reasons.append(f"builds < {min_builds}")
    if stats.failure_rate < failure_rate_threshold:
        reasons.append(f"failure rate < {failure_rate_threshold:.0%}")
    return "NOT SELECTED" if not reasons else "NOT SELECTED (" + ", ".join(reasons) + ")"


def print_summary(stats_list: list[ProjectStats], selected_projects: set[str]) -> None:
    headers = ("Project", "Builds", "Tests", "Failure Rate", "Qualifies")
    rows = [
        (
            stats.project,
            str(stats.build_count),
            str(stats.test_count),
            f"{stats.failure_rate:.2%}",
            "yes" if stats.qualifies else "no",
        )
        for stats in stats_list
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    print()
    print(
        " | ".join(
            header.ljust(widths[index]) for index, header in enumerate(headers)
        )
    )
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(
            " | ".join(
                value.ljust(widths[index]) for index, value in enumerate(row)
            )
        )
    print()


def write_markdown_summary(
    summary_path: Path,
    stats_list: list[ProjectStats],
    selected_projects: set[str],
    min_builds: int,
    failure_rate_threshold: float,
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "| Project | Builds | Tests | Failure Rate | Status |",
        "|---------|--------|-------|--------------|--------|",
    ]
    for stats in stats_list:
        status = status_for(
            stats,
            selected_projects,
            min_builds=min_builds,
            failure_rate_threshold=failure_rate_threshold,
        )
        lines.append(
            "| "
            f"{stats.project} | "
            f"{stats.build_count} | "
            f"{stats.test_count} | "
            f"{stats.failure_rate:.2%} | "
            f"{status} |"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rtp_path = args.rtp_path
    mapping_path = rtp_path / "tr_all_built_commits.csv"

    print(f"Loading mapping from {mapping_path}...")
    mapping_job_ids = read_mapping_job_ids(mapping_path)

    stats_list: list[ProjectStats] = []
    for project_dir in iter_project_dirs(rtp_path):
        print(f"Processing {project_dir.name}...")
        stats = analyze_project(
            project_dir=project_dir,
            mapping_job_ids=mapping_job_ids,
            failure_rate_threshold=args.failure_rate_threshold,
            min_builds=args.min_builds,
        )
        stats_list.append(stats)

    stats_list.sort(key=lambda stats: stats.project.lower())
    qualified = sorted(
        (stats for stats in stats_list if stats.qualifies),
        key=lambda stats: stats.failure_rate,
        reverse=True,
    )
    selected = qualified[: args.limit]
    selected_projects = {stats.project for stats in selected}

    print_summary(stats_list, selected_projects)
    write_markdown_summary(
        args.summary_path,
        stats_list,
        selected_projects,
        min_builds=args.min_builds,
        failure_rate_threshold=args.failure_rate_threshold,
    )
    print(f"Saved summary to {args.summary_path}")
    print(f"Selected projects: {[stats.project for stats in selected]}")

    if len(selected) < args.min_selected:
        raise RuntimeError(
            f"Only {len(selected)} projects qualified; at least "
            f"{args.min_selected} are required. Adjust selection criteria."
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
