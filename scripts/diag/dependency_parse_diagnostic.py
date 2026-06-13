#!/usr/bin/env python3
"""Diagnose root causes behind ``dependency_parse_failed`` rows.

The production feature flag currently conflates two different cases:
missing test source files and Java parser exceptions. This script keeps the
feature pipeline unchanged and reports those causes separately.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable

import javalang
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.dependency_extractor import DependencyFeatureExtractor


@dataclass(frozen=True)
class WorktreeResult:
    repo: str
    test_id: str
    expected_path: str
    located_path: str
    category: str
    detail: str


@dataclass(frozen=True)
class HistoricalResult:
    repo: str
    commit_sha: str
    test_id: str
    tree_status: str
    candidates: tuple[str, ...]
    blob_status: str
    parse_status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify dependency_parse_failed rows by root cause."
    )
    parser.add_argument(
        "--feature-path",
        default=None,
        help="Optional parquet file to inspect, for example data/features/full_features.parquet.",
    )
    parser.add_argument(
        "--feature-dir",
        default="data/features",
        help="Directory containing per-project *_features.parquet files.",
    )
    parser.add_argument(
        "--git-root",
        default="data/git-repos",
        help="Root containing local clones named <owner>@<repo>.",
    )
    parser.add_argument(
        "--sample-per-category",
        type=int,
        default=5,
        help="Number of worktree examples to print per repo/category.",
    )
    parser.add_argument(
        "--historical-samples",
        type=int,
        default=5,
        help="Rows per repo to inspect in historical commit trees for worktree-missing tests.",
    )
    parser.add_argument(
        "--output-markdown",
        default=None,
        help="Optional markdown report path.",
    )
    return parser.parse_args()


def load_features(feature_path: str | None, feature_dir: str | Path) -> pd.DataFrame:
    if feature_path:
        path = Path(feature_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return pd.read_parquet(path)

    feature_root = Path(feature_dir)
    full_features = feature_root / "full_features.parquet"
    if full_features.exists():
        return pd.read_parquet(full_features)

    parquet_files = sorted(feature_root.glob("*_features.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No feature parquet files found under {feature_root}")
    frames = [pd.read_parquet(path) for path in parquet_files]
    return pd.concat(frames, ignore_index=True)


def require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"Feature data is missing required columns: {sorted(missing)}")


def diagnose_worktree(
    extractor: DependencyFeatureExtractor,
    git_root: Path,
    repo: str,
    test_id: str,
) -> WorktreeResult:
    repo_root = git_root / repo
    expected_path = extractor._test_id_to_path(test_id)
    located_path = extractor._find_test_file(repo_root, expected_path)
    expected_text = extractor._normalize_path(expected_path)

    if not repo_root.exists():
        return WorktreeResult(
            repo=repo,
            test_id=test_id,
            expected_path=expected_text,
            located_path="",
            category="repo_missing",
            detail=f"Repository path does not exist: {repo_root}",
        )

    if not located_path.exists():
        return WorktreeResult(
            repo=repo,
            test_id=test_id,
            expected_path=expected_text,
            located_path=extractor._normalize_path(located_path),
            category="worktree_file_missing",
            detail="No matching test source found in current checkout.",
        )

    try:
        source = located_path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - depends on filesystem state.
        return WorktreeResult(
            repo=repo,
            test_id=test_id,
            expected_path=expected_text,
            located_path=extractor._normalize_path(located_path.relative_to(repo_root)),
            category="source_read_error",
            detail=short_exception(exc),
        )

    try:
        javalang.parse.parse(source)
    except Exception as exc:
        return WorktreeResult(
            repo=repo,
            test_id=test_id,
            expected_path=expected_text,
            located_path=extractor._normalize_path(located_path.relative_to(repo_root)),
            category="javalang_parse_exception",
            detail=short_exception(exc),
        )

    return WorktreeResult(
        repo=repo,
        test_id=test_id,
        expected_path=expected_text,
        located_path=extractor._normalize_path(located_path.relative_to(repo_root)),
        category="stale_feature_artifact",
        detail="Current source exists and javalang parses it, but parquet row is flagged failed.",
    )


def inspect_historical_commit(
    git_root: Path,
    repo: str,
    commit_sha: str,
    test_id: str,
    max_candidates: int = 3,
) -> HistoricalResult:
    repo_root = git_root / repo
    class_file = f"{test_id.split('.')[-1]}.java"
    package_suffix = "src/test/java/" + "/".join(test_id.split(".")) + ".java"
    if not repo_root.exists():
        return HistoricalResult(repo, commit_sha, test_id, "repo_missing", (), "", "", "")

    tree = run_git(repo_root, "ls-tree", "-r", "--name-only", commit_sha)
    if tree.returncode != 0:
        return HistoricalResult(
            repo=repo,
            commit_sha=commit_sha,
            test_id=test_id,
            tree_status="tree_unavailable",
            candidates=(),
            blob_status="not_checked",
            parse_status="not_checked",
            detail=short_text(tree.stderr),
        )

    paths = [line.strip() for line in tree.stdout.splitlines() if line.strip()]
    exact_suffix_matches = [
        path for path in paths if path == package_suffix or path.endswith(f"/{package_suffix}")
    ]
    filename_matches = [
        path
        for path in paths
        if path.endswith(f"/{class_file}") and "/src/test/java/" in f"/{path}"
    ]
    candidates = tuple((exact_suffix_matches or filename_matches)[:max_candidates])
    if not candidates:
        return HistoricalResult(
            repo=repo,
            commit_sha=commit_sha,
            test_id=test_id,
            tree_status="not_in_commit_tree",
            candidates=(),
            blob_status="not_checked",
            parse_status="not_checked",
            detail="No src/test/java candidate in commit tree.",
        )

    blob_statuses: list[str] = []
    parse_statuses: list[str] = []
    details: list[str] = []
    for path in candidates:
        blob = run_git(repo_root, "cat-file", "-e", f"{commit_sha}:{path}")
        if blob.returncode != 0:
            blob_statuses.append("blob_missing_or_lazy_fetch_required")
            parse_statuses.append("not_checked")
            details.append(short_text(blob.stderr))
            continue

        blob_statuses.append("blob_available")
        show = run_git(repo_root, "show", f"{commit_sha}:{path}")
        if show.returncode != 0:
            parse_statuses.append("source_unavailable")
            details.append(short_text(show.stderr))
            continue
        try:
            javalang.parse.parse(show.stdout)
            parse_statuses.append("javalang_parse_ok")
            details.append("")
        except Exception as exc:
            parse_statuses.append("javalang_parse_exception")
            details.append(short_exception(exc))

    return HistoricalResult(
        repo=repo,
        commit_sha=commit_sha,
        test_id=test_id,
        tree_status="candidate_found",
        candidates=candidates,
        blob_status=";".join(blob_statuses),
        parse_status=";".join(parse_statuses),
        detail=" | ".join(detail for detail in details if detail),
    )


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_NO_LAZY_FETCH"] = "1"
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def short_exception(exc: Exception, limit: int = 180) -> str:
    return short_text(f"{type(exc).__name__}: {exc}", limit=limit)


def short_text(text: str, limit: int = 180) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def pct(part: int | float, whole: int | float) -> str:
    if not whole:
        return "0.0%"
    return f"{100 * float(part) / float(whole):.1f}%"


def markdown_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def build_report(
    df: pd.DataFrame,
    failed: pd.DataFrame,
    worktree_results: dict[tuple[str, str], WorktreeResult],
    historical_results: list[HistoricalResult],
    sample_per_category: int,
) -> str:
    lines: list[str] = []
    lines.append("# Dependency Parse Diagnostic")
    lines.append("")
    lines.append(
        "Classifies `dependency_parse_failed=1` rows into worktree/file-availability "
        "issues versus `javalang` parser exceptions. Historical checks use "
        "`GIT_NO_LAZY_FETCH=1` so blobless clones do not silently fetch missing blobs."
    )
    lines.append("")

    summary_rows: list[list[object]] = []
    for repo, group in df.groupby("repo", sort=True):
        failed_group = failed[failed["repo"] == repo]
        summary_rows.append(
            [
                repo,
                len(group),
                len(failed_group),
                pct(len(failed_group), len(group)),
                failed_group["test_id"].nunique(),
                group["test_id"].nunique(),
            ]
        )
    lines.extend(
        markdown_table(
            [
                "Repo",
                "Rows",
                "Failed rows",
                "Failed rate",
                "Failed unique tests",
                "Total unique tests",
            ],
            summary_rows,
        )
    )
    lines.append("")

    category_rows: list[list[object]] = []
    unique_by_category: Counter[tuple[str, str]] = Counter()
    row_by_category: Counter[tuple[str, str]] = Counter()
    for (repo, test_id), result in worktree_results.items():
        unique_by_category[(repo, result.category)] += 1
    for _, row in failed.iterrows():
        result = worktree_results[(str(row["repo"]), str(row["test_id"]))]
        row_by_category[(result.repo, result.category)] += 1
    for repo in sorted(failed["repo"].dropna().unique()):
        for category in sorted(
            category for item_repo, category in row_by_category if item_repo == repo
        ):
            rows = row_by_category[(repo, category)]
            category_rows.append(
                [
                    repo,
                    category,
                    rows,
                    pct(rows, len(failed[failed["repo"] == repo])),
                    unique_by_category[(repo, category)],
                ]
            )
    lines.extend(
        markdown_table(
            ["Repo", "Category", "Failed rows", "Share of failed", "Unique tests"],
            category_rows,
        )
    )
    lines.append("")

    lines.append("## Worktree Examples")
    examples: dict[tuple[str, str], list[WorktreeResult]] = defaultdict(list)
    for result in worktree_results.values():
        key = (result.repo, result.category)
        if len(examples[key]) < sample_per_category:
            examples[key].append(result)
    for key in sorted(examples):
        repo, category = key
        lines.append("")
        lines.append(f"### {repo} / {category}")
        rows = [
            [item.test_id, item.expected_path, item.located_path, item.detail]
            for item in examples[key]
        ]
        lines.extend(markdown_table(["Test id", "Expected path", "Located path", "Detail"], rows))

    if historical_results:
        lines.append("")
        lines.append("## Historical Commit Samples")
        rows = []
        for item in historical_results:
            rows.append(
                [
                    item.repo,
                    item.commit_sha[:12],
                    item.test_id,
                    item.tree_status,
                    "<br>".join(item.candidates),
                    item.blob_status,
                    item.parse_status,
                    item.detail,
                ]
            )
        lines.extend(
            markdown_table(
                [
                    "Repo",
                    "Commit",
                    "Test id",
                    "Tree status",
                    "Candidates",
                    "Blob status",
                    "Parse status",
                    "Detail",
                ],
                rows,
            )
        )

    lines.append("")
    lines.append("## Interpretation Guide")
    lines.append("")
    lines.append(
        "- `worktree_file_missing`: the current extractor cannot locate the test source "
        "in the checked-out repo snapshot. This can be a checkout/history issue or a "
        "test-id-to-path mismatch, but it is not a `javalang` syntax failure."
    )
    lines.append(
        "- `candidate_found` plus `blob_available`: the historical commit contains a "
        "matching test file and the local clone can read it without lazy fetch."
    )
    lines.append(
        "- `candidate_found` plus `blob_missing_or_lazy_fetch_required`: the historical "
        "commit tree names the file, but the local clone lacks the blob locally."
    )
    lines.append(
        "- `javalang_parse_exception`: the file exists/read succeeds, so parser "
        "replacement or fallback parsing is the relevant fix."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    df = load_features(args.feature_path, args.feature_dir)
    require_columns(df, ["repo", "test_id", "commit_sha", "dependency_parse_failed"])

    failed = df[df["dependency_parse_failed"] == 1].copy()
    extractor = DependencyFeatureExtractor()
    git_root = Path(args.git_root)

    worktree_results: dict[tuple[str, str], WorktreeResult] = {}
    unique_failed = failed[["repo", "test_id"]].drop_duplicates()
    for row in unique_failed.itertuples(index=False):
        repo = str(row.repo)
        test_id = str(row.test_id)
        worktree_results[(repo, test_id)] = diagnose_worktree(
            extractor=extractor,
            git_root=git_root,
            repo=repo,
            test_id=test_id,
        )

    historical_results: list[HistoricalResult] = []
    if args.historical_samples > 0:
        for repo in sorted(failed["repo"].dropna().unique()):
            repo_failed = failed[failed["repo"] == repo]
            if "commit_meta_missing" in repo_failed.columns:
                preferred = repo_failed[repo_failed["commit_meta_missing"] == 0]
                if not preferred.empty:
                    repo_failed = preferred
            missing_rows = []
            for row in repo_failed.itertuples(index=False):
                key = (str(row.repo), str(row.test_id))
                if worktree_results[key].category != "worktree_file_missing":
                    continue
                if pd.isna(row.commit_sha):
                    continue
                missing_rows.append((str(row.commit_sha), str(row.test_id)))
            seen: set[tuple[str, str]] = set()
            for commit_sha, test_id in missing_rows:
                sample_key = (commit_sha, test_id)
                if sample_key in seen:
                    continue
                seen.add(sample_key)
                historical_results.append(
                    inspect_historical_commit(git_root, str(repo), commit_sha, test_id)
                )
                if len(seen) >= args.historical_samples:
                    break

    report = build_report(
        df=df,
        failed=failed,
        worktree_results=worktree_results,
        historical_results=historical_results,
        sample_per_category=args.sample_per_category,
    )
    print(report)

    if args.output_markdown:
        output_path = Path(args.output_markdown)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
