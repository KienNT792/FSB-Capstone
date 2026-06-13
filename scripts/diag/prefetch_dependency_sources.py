#!/usr/bin/env python3
"""Prefetch historical test-source blobs needed by dependency features.

This is an explicit recovery step for partial/blobless clones. It asks Git for
only the ``commit:path`` objects that the dependency extractor may read, instead
of unfiltering every blob in a large monorepo.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.dependency_extractor import DependencyFeatureExtractor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prefetch historical Java test-source blobs for one project."
    )
    parser.add_argument("--project", required=True, help="Project id, e.g. deeplearning4j@deeplearning4j.")
    parser.add_argument("--db-path", default="data/test_history.db", help="DuckDB database path.")
    parser.add_argument("--git-root", default="data/git-repos", help="Root containing local clones.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print candidate counts without asking Git to fetch blobs.",
    )
    return parser.parse_args()


def load_project_rows(project: str, db_path: str | Path) -> tuple[list[tuple[str, str]], list[str]]:
    with duckdb.connect(str(db_path), read_only=True) as con:
        test_rows = con.execute(
            """
            SELECT DISTINCT commit_sha, test_id
            FROM test_runs
            WHERE repo = ? AND commit_sha IS NOT NULL
            """,
            [project],
        ).fetchall()
        changed_paths = [
            str(row[0])
            for row in con.execute(
                "SELECT file_path FROM file_changes WHERE repo = ?",
                [project],
            ).fetchall()
        ]
    return [(str(sha), str(test_id)) for sha, test_id in test_rows], changed_paths


def build_specs(project: str, db_path: str | Path, repo_path: Path) -> list[str]:
    rows, changed_paths = load_project_rows(project, db_path)
    extractor = DependencyFeatureExtractor()
    extractor.add_observed_test_source_paths(changed_paths)

    specs: set[str] = set()
    for commit_sha, test_id in rows:
        test_rel = extractor._test_id_to_path(test_id)
        worktree_path = extractor._find_test_file(repo_path, test_rel, test_id)
        if worktree_path.exists():
            continue
        for candidate in extractor._candidate_test_paths(test_id, test_rel):
            specs.add(f"{commit_sha}:{candidate}")
    return sorted(specs)


def prefetch(repo_path: Path, specs: list[str]) -> tuple[int, int, int]:
    if not specs:
        return 0, 0, 0
    result = subprocess.run(
        ["git", "cat-file", "--batch-check"],
        cwd=str(repo_path),
        input="\n".join(specs) + "\n",
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git cat-file --batch-check failed")

    blob_count = 0
    missing_count = 0
    other_count = 0
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "blob":
            blob_count += 1
        elif parts and parts[-1] == "missing":
            missing_count += 1
        else:
            other_count += 1
    return blob_count, missing_count, other_count


def main() -> int:
    args = parse_args()
    repo_path = Path(args.git_root) / args.project
    if not repo_path.exists():
        raise FileNotFoundError(repo_path)

    specs = build_specs(args.project, args.db_path, repo_path)
    print(f"Project: {args.project}")
    print(f"Candidate commit:path specs: {len(specs)}")
    if args.dry_run:
        for spec in specs[:20]:
            print(f"  {spec}")
        if len(specs) > 20:
            print(f"  ... {len(specs) - 20} more")
        return 0

    blob_count, missing_count, other_count = prefetch(repo_path, specs)
    print(
        "Done. "
        f"blob specs available/fetched: {blob_count}; "
        f"missing specs: {missing_count}; other: {other_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
