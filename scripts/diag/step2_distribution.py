"""Step 2: Distribution check for test_file_touched and same_package features."""

from __future__ import annotations

import pandas as pd
from pathlib import Path


def main() -> None:
    parquet_files = sorted(Path("data/features").glob("*_features.parquet"))
    print(f"Loading {len(parquet_files)} parquet files...")
    dfs = [pd.read_parquet(p) for p in parquet_files]
    df = pd.concat(dfs, ignore_index=True)
    print(f"Total rows: {len(df)}")
    print(f"Repos: {df['repo'].unique().tolist()}")
    print()

    for feature in ["test_file_touched", "same_package"]:
        print(f"{'='*60}")
        print(f"=== {feature} ===")
        print(f"{'='*60}")

        print("\n--- value_counts (overall) ---")
        print(df[feature].value_counts(dropna=False))

        print(f"\n--- fraction = 1 overall: {(df[feature] == 1).mean():.6f} ---")

        print("\n--- value_counts by repo (normalized) ---")
        for repo, grp in df.groupby("repo"):
            vc = grp[feature].value_counts(dropna=False)
            frac_1 = (grp[feature] == 1).mean()
            print(f"  {repo}: {dict(vc)}  | frac=1: {frac_1:.6f}")

        print("\n--- crosstab with label ---")
        ct = pd.crosstab(df[feature], df["label"], margins=True)
        print(ct)

        print()


if __name__ == "__main__":
    main()
