"""Step 3b: Targeted trace - pick rows with feature=1 and cross-check against file_changes."""

from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path


DB_PATH = "data/test_history.db"
REPO = "neuland@jade4j"


def normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def test_id_to_rel_path(test_id: str) -> str:
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
    feat_path = Path("data/features") / f"{REPO}_features.parquet"
    df = pd.read_parquet(feat_path)

    # Subset: commit known, parse ok
    valid = df[
        df["commit_sha"].notna()
        & (df["commit_meta_missing"] == 0)
        & (df["dependency_parse_failed"] == 0)
    ].copy()

    # Pick rows where test_file_touched=1 (true positives per feature)
    touched_1 = valid[valid["test_file_touched"] == 1].sample(n=min(3, (valid["test_file_touched"] == 1).sum()), random_state=7)
    # Pick rows where same_package=1
    pkg_1 = valid[valid["same_package"] == 1].sample(n=min(3, (valid["same_package"] == 1).sum()), random_state=7)

    print(f"Rows with test_file_touched=1 (parse ok): {(valid['test_file_touched']==1).sum()}")
    print(f"Rows with same_package=1 (parse ok): {(valid['same_package']==1).sum()}")
    print()

    with duckdb.connect(DB_PATH, read_only=True) as con:
        path_col = "file_path"

        def get_changed(sha: str) -> list[str]:
            rows = con.execute(
                f"SELECT {path_col} FROM file_changes WHERE commit_sha = ? AND repo = ?",
                [sha, REPO],
            ).fetchall()
            return [normalize_path(str(r[0])) for r in rows]

        print("="*90)
        print("TEST_FILE_TOUCHED: tracing 3 rows where feature=1")
        print("="*90)
        for _, row in touched_1.iterrows():
            sha = str(row["commit_sha"])
            test_id = str(row["test_id"])
            changed_paths = get_changed(sha)
            test_rel = normalize_path(test_id_to_rel_path(test_id))
            test_filename = test_rel.split("/")[-1]

            exact_match = test_rel in changed_paths
            filename_match = any(p.endswith(test_filename) for p in changed_paths)
            manual_val = int(exact_match or filename_match)
            actual_val = int(row["test_file_touched"])

            print(f"\n  commit: {sha[:12]}  test_id: {test_id}")
            print(f"  expected_test_rel: {test_rel}")
            print(f"  changed_paths ({len(changed_paths)}): {changed_paths}")
            print(f"  exact_match={exact_match}  filename_match={filename_match}")
            print(f"  manual={manual_val}  actual={actual_val}  match={'Y' if manual_val==actual_val else 'N'}")

        print()
        print("="*90)
        print("SAME_PACKAGE: tracing 3 rows where feature=1")
        print("="*90)
        for _, row in pkg_1.iterrows():
            sha = str(row["commit_sha"])
            test_id = str(row["test_id"])
            changed_paths = get_changed(sha)
            pkg = test_id_to_package(test_id)
            changed_packages = [path_to_package(p) for p in changed_paths]
            manual_val = int(any(cp == pkg for cp in changed_packages if cp))
            actual_val = int(row["same_package"])

            print(f"\n  commit: {sha[:12]}  test_id: {test_id}")
            print(f"  test_package: {pkg}")
            print(f"  changed_paths ({len(changed_paths)}): {changed_paths}")
            print(f"  changed_packages: {changed_packages}")
            print(f"  manual={manual_val}  actual={actual_val}  match={'Y' if manual_val==actual_val else 'N'}")

        # --- Also check deeplearning4j which has same_package=0 for ALL rows ---
        print()
        print("="*90)
        print("DEEPLEARNING4J: checking why same_package=0 for all 15509 rows")
        print("="*90)
        dl4j_feat = pd.read_parquet("data/features/deeplearning4j@deeplearning4j_features.parquet")
        dl4j_valid = dl4j_feat[dl4j_feat["commit_sha"].notna()].head(5)
        for _, row in dl4j_valid.iterrows():
            sha = str(row["commit_sha"])
            rows = con.execute(
                f"SELECT {path_col} FROM file_changes WHERE commit_sha = ? AND repo = ?",
                [sha, "deeplearning4j@deeplearning4j"],
            ).fetchall()
            changed_paths = [normalize_path(str(r[0])) for r in rows]
            print(f"  commit {sha[:12]}: {len(changed_paths)} changed files")
            if changed_paths:
                print(f"    sample: {changed_paths[:3]}")

        # Check how many file_changes rows exist for deeplearning4j
        total_dl4j = con.execute(
            "SELECT COUNT(*) FROM file_changes WHERE repo = ?",
            ["deeplearning4j@deeplearning4j"],
        ).fetchone()[0]
        print(f"\n  Total file_changes rows for deeplearning4j: {total_dl4j}")

        # Check dependency_parse_failed for deeplearning4j
        dl4j_parse_fail = dl4j_feat["dependency_parse_failed"].value_counts()
        print(f"  dependency_parse_failed: {dl4j_parse_fail.to_dict()}")


if __name__ == "__main__":
    main()
