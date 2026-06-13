"""Step 3: Manual trace for test_file_touched and same_package on neuland@jade4j rows."""

from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path


DB_PATH = "data/test_history.db"
REPO = "neuland@jade4j"


def normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def test_id_to_rel_path(test_id: str) -> str:
    """e.g. de.neuland.jade4j.FooTest -> src/test/java/de/neuland/jade4j/FooTest.java"""
    parts = test_id.split(".")
    return "src/test/java/" + "/".join(parts) + ".java"


def test_id_to_package(test_id: str) -> str:
    parts = test_id.split(".")
    return ".".join(parts[:-1])


def path_to_package(path: str) -> str:
    normalized = normalize_path(path)
    for marker in ("src/main/java/", "src/test/java/"):
        if marker in normalized:
            package_path = normalized.split(marker, 1)[1]
            parts = package_path.split("/")[:-1]
            return ".".join(parts)
    return ""


def main() -> None:
    # Load feature parquet for jade4j
    feat_path = Path("data/features") / f"{REPO}_features.parquet"
    df = pd.read_parquet(feat_path)
    print(f"jade4j rows: {len(df)}")
    print(f"commit_meta_missing distribution: {df['commit_meta_missing'].value_counts().to_dict()}")
    print(f"dependency_parse_failed distribution: {df['dependency_parse_failed'].value_counts().to_dict()}")

    # Pick rows where commit_sha is not null and dependency_parse_failed=0
    candidates = df[
        df["commit_sha"].notna()
        & (df["commit_meta_missing"] == 0)
        & (df["dependency_parse_failed"] == 0)
    ].copy()
    print(f"\nCandidate rows (commit known, parse ok): {len(candidates)}")

    # Sample 3 rows
    sample = candidates.sample(n=min(3, len(candidates)), random_state=42)
    print(f"\nSampled {len(sample)} rows:")
    print(sample[["commit_sha", "test_id", "test_file_touched", "same_package", "label"]].to_string())

    # For each row, look up file_changes in DuckDB
    with duckdb.connect(DB_PATH, read_only=True) as con:
        # Check column name
        cols = {row[0] for row in con.execute("DESCRIBE file_changes").fetchall()}
        path_col = "file_path" if "file_path" in cols else "filepath"
        print(f"\nfile_changes path column: {path_col}")
        print(f"file_changes columns: {cols}")

        print("\n" + "="*80)
        print("MANUAL TRACE TABLE")
        print("="*80)
        header = f"{'commit_sha':>12}  {'test_id':>45}  {'feature':>18}  {'expected':>8}  {'actual':>6}  {'match':>5}"
        print(header)
        print("-" * len(header))

        for _, row in sample.iterrows():
            sha = str(row["commit_sha"])
            test_id = str(row["test_id"])

            changed_files = con.execute(
                f"SELECT {path_col} FROM file_changes WHERE commit_sha = ? AND repo = ?",
                [sha, REPO],
            ).fetchall()
            changed_paths = [normalize_path(str(r[0])) for r in changed_files]

            # --- test_file_touched ---
            test_rel = normalize_path(test_id_to_rel_path(test_id))
            # also check bare filename match
            test_filename = test_rel.split("/")[-1]
            manual_touched = int(
                test_rel in changed_paths
                or any(p.endswith(test_filename) for p in changed_paths)
            )
            actual_touched = int(row["test_file_touched"])
            match_touched = "Y" if manual_touched == actual_touched else "N"
            print(f"{sha[:12]:>12}  {test_id:>45}  {'test_file_touched':>18}  {manual_touched:>8}  {actual_touched:>6}  {match_touched:>5}")
            if changed_paths:
                print(f"             changed_paths ({len(changed_paths)}): {changed_paths[:5]}")
                print(f"             expected_test_rel: {test_rel}")
            else:
                print(f"             NO changed files found in file_changes for this commit")

            # --- same_package ---
            pkg = test_id_to_package(test_id)
            changed_packages = [path_to_package(p) for p in changed_paths]
            manual_same_pkg = int(any(cp == pkg for cp in changed_packages if cp))
            actual_same_pkg = int(row["same_package"])
            match_same_pkg = "Y" if manual_same_pkg == actual_same_pkg else "N"
            print(f"{sha[:12]:>12}  {test_id:>45}  {'same_package':>18}  {manual_same_pkg:>8}  {actual_same_pkg:>6}  {match_same_pkg:>5}")
            print(f"             test_package: {pkg}")
            print(f"             changed_packages: {list(set(changed_packages))[:5]}")
            print()


if __name__ == "__main__":
    main()
