"""Extra checks: deeplearning4j path formats, parse_failed breakdown, and low-positive analysis."""

from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path


DB_PATH = "data/test_history.db"


def normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def path_to_package(path: str) -> str:
    normalized = normalize_path(path)
    for marker in ("src/main/java/", "src/test/java/"):
        if marker in normalized:
            package_path = normalized.split(marker, 1)[1]
            parts = package_path.split("/")[:-1]
            return ".".join(parts)
    return ""


def main() -> None:
    with duckdb.connect(DB_PATH, read_only=True) as con:
        # Sample file_changes paths for deeplearning4j (non-trivial ones)
        print("=== deeplearning4j sample file_changes paths ===")
        rows = con.execute(
            "SELECT DISTINCT file_path FROM file_changes WHERE repo = ? LIMIT 20",
            ["deeplearning4j@deeplearning4j"],
        ).fetchall()
        for r in rows:
            p = normalize_path(str(r[0]))
            pkg = path_to_package(p)
            print(f"  path={p!r}  -> package={pkg!r}")

        # How many deeplearning4j file_changes have src/main/java or src/test/java?
        print("\n=== deeplearning4j: paths containing src/main/java or src/test/java ===")
        total = con.execute(
            "SELECT COUNT(*) FROM file_changes WHERE repo = ?",
            ["deeplearning4j@deeplearning4j"],
        ).fetchone()[0]
        java_main = con.execute(
            "SELECT COUNT(*) FROM file_changes WHERE repo = ? AND file_path LIKE '%src/main/java%'",
            ["deeplearning4j@deeplearning4j"],
        ).fetchone()[0]
        java_test = con.execute(
            "SELECT COUNT(*) FROM file_changes WHERE repo = ? AND file_path LIKE '%src/test/java%'",
            ["deeplearning4j@deeplearning4j"],
        ).fetchone()[0]
        print(f"  total: {total}, has src/main/java: {java_main}, has src/test/java: {java_test}")

        # What path formats exist for deeplearning4j?
        print("\n=== deeplearning4j path prefixes (first 3 components) ===")
        rows = con.execute(
            "SELECT file_path, COUNT(*) as cnt FROM file_changes WHERE repo = ? GROUP BY file_path ORDER BY cnt DESC LIMIT 10",
            ["deeplearning4j@deeplearning4j"],
        ).fetchall()
        for r in rows:
            print(f"  {r[0]!r}: {r[1]}")

        # Same for thinkaurelius@titan - low but nonzero same_package
        print("\n=== thinkaurelius@titan sample file_changes paths ===")
        rows = con.execute(
            "SELECT DISTINCT file_path FROM file_changes WHERE repo = ? LIMIT 15",
            ["thinkaurelius@titan"],
        ).fetchall()
        for r in rows:
            p = normalize_path(str(r[0]))
            pkg = path_to_package(p)
            print(f"  path={p!r}  -> package={pkg!r}")

    # Summary: parse_failed rate per repo
    print("\n=== dependency_parse_failed per repo ===")
    for pf in Path("data/features").glob("*_features.parquet"):
        df = pd.read_parquet(pf)
        repo = df["repo"].iloc[0]
        total = len(df)
        failed = (df["dependency_parse_failed"] == 1).sum()
        pct = 100 * failed / total if total > 0 else 0
        print(f"  {repo}: {failed}/{total} parse_failed ({pct:.1f}%)")
        # also check what fraction of non-failed rows have test_file_touched=1 or same_package=1
        ok = df[df["dependency_parse_failed"] == 0]
        if len(ok) > 0:
            tft = (ok["test_file_touched"] == 1).mean()
            sp = (ok["same_package"] == 1).mean()
            print(f"    (parse_ok rows={len(ok)}) test_file_touched=1: {tft:.4f}, same_package=1: {sp:.4f}")


if __name__ == "__main__":
    main()
