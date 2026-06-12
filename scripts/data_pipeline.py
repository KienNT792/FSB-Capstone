#!/usr/bin/env python3
"""Run Sprint 2 feature extraction for one RTPTorrent project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.feature_joiner import FeatureJoiner
from src.features.validation import validate_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Sprint 2 feature parquet for one project.")
    parser.add_argument("--project", required=True, help="RTPTorrent project identifier, e.g. neuland@jade4j.")
    parser.add_argument("--db-path", default="data/test_history.db", help="DuckDB database path.")
    parser.add_argument("--rtp-path", default="data/repos/rtp-torrent", help="RTPTorrent dataset root.")
    parser.add_argument("--output-path", default=None, help="Output parquet path.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output parquet.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output_path or f"data/features/{args.project}_features.parquet")

    if output_path.exists() and not args.force:
        print("Output exists. Use --force to overwrite.")
        return 0

    # rtp_path is accepted for CLI stability; feature extraction reads the
    # Sprint 1 DuckDB artifact and local git clones.
    _ = args.rtp_path

    joiner = FeatureJoiner(output_dir=output_path.parent)
    df = joiner.build(args.project, args.db_path)
    validate_features(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    label_distribution = df["label"].value_counts().sort_index().to_dict()
    commit_meta_missing = int(df["commit_meta_missing"].sum()) if "commit_meta_missing" in df else 0
    print(
        f"Done. Shape: {df.shape}. Label distribution: {label_distribution}. "
        f"commit_meta_missing: {commit_meta_missing} rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
