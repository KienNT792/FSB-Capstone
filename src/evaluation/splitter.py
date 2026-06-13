"""Temporal train/test split for per-project AdaptCI feature DataFrames."""

from __future__ import annotations

import logging
import math

import pandas as pd

logger = logging.getLogger(__name__)


def temporal_split(
    df: pd.DataFrame,
    train_ratio: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a single-project feature DataFrame into train and test by job_sequence.

    Split unit: job_sequence (DENSE_RANK on job_id, always non-null).
    All rows sharing a job_sequence value belong to the same CI job and
    land in the same split — no CI run is ever split across sets.

    NULL commit_sha rows are distributed proportionally across train and test
    according to their position in the build timeline. They are never excluded.

    Args:
        df: Feature DataFrame for exactly one project.
            Caller must filter full_features.parquet by repo before passing.
        train_ratio: Fraction of job sequences to place in train (default 0.8).

    Returns:
        (train_df, test_df) — both retain all original columns.

    Raises:
        ValueError: If df contains rows from more than one project, or if
            job_sequence column is missing.
    """
    if "job_sequence" not in df.columns:
        raise ValueError("DataFrame is missing required column 'job_sequence'.")

    repos = df["repo"].dropna().unique()
    if len(repos) != 1:
        raise ValueError(
            f"temporal_split requires a single-project DataFrame; "
            f"got repos: {sorted(str(r) for r in repos)}"
        )

    max_seq = int(df["job_sequence"].max())
    threshold = math.floor(train_ratio * max_seq)

    train_df = df[df["job_sequence"] <= threshold].copy()
    test_df = df[df["job_sequence"] > threshold].copy()

    # Guaranteed by threshold construction, but assert defensively.
    train_seqs = set(train_df["job_sequence"].unique())
    test_seqs = set(test_df["job_sequence"].unique())
    overlap = train_seqs & test_seqs
    assert not overlap, f"job_sequence overlap in split: {overlap}"

    logger.info(
        "%s — Train: %d jobs, %d rows (%d non-null SHAs). "
        "Test: %d jobs, %d rows (%d non-null SHAs). Split at seq %d/%d.",
        repos[0],
        train_df["job_sequence"].nunique(),
        len(train_df),
        int(train_df["commit_sha"].notna().sum()),
        test_df["job_sequence"].nunique(),
        len(test_df),
        int(test_df["commit_sha"].notna().sum()),
        threshold,
        max_seq,
    )
    return train_df, test_df
