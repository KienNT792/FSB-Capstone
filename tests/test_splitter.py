"""Unit tests for temporal_split (G1/G2 correctness)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.evaluation.splitter import temporal_split


def make_project_df(
    n_jobs: int = 10,
    tests_per_job: int = 3,
    repo: str = "owner@repo",
    null_sha_jobs: list[int] | None = None,
) -> pd.DataFrame:
    """Build a minimal single-project feature DataFrame for testing.

    Args:
        n_jobs: Number of distinct CI jobs (job_sequence 1..n_jobs).
        tests_per_job: Number of test rows per job.
        repo: Project identifier.
        null_sha_jobs: job_sequence values that should have NULL commit_sha.
            Defaults to [3, 7] when n_jobs >= 8, else empty.
    """
    if null_sha_jobs is None:
        null_sha_jobs = [3, 7] if n_jobs >= 8 else []

    rows = []
    for seq in range(1, n_jobs + 1):
        sha = None if seq in null_sha_jobs else f"sha{seq:04d}"
        ts = seq * 1000 if sha is not None else None
        for t in range(tests_per_job):
            rows.append(
                {
                    "repo": repo,
                    "job_sequence": seq,
                    "commit_sha": sha,
                    "test_id": f"com.example.Test{t}",
                    "label": 0,
                    "timestamp": ts,
                    "feature_source": "timestamp" if ts is not None else "job_sequence",
                    "days_since_last_fail": 999.0,
                }
            )
    return pd.DataFrame(rows)


def test_single_project_required() -> None:
    df = make_project_df()
    extra = df.copy()
    extra["repo"] = "other@project"
    mixed = pd.concat([df, extra], ignore_index=True)

    with pytest.raises(ValueError, match="single-project"):
        temporal_split(mixed)


def test_missing_job_sequence_column_raises() -> None:
    df = make_project_df().drop(columns=["job_sequence"])

    with pytest.raises(ValueError, match="job_sequence"):
        temporal_split(df)


def test_basic_80_20_split() -> None:
    df = make_project_df(n_jobs=10, tests_per_job=2)
    train, test = temporal_split(df, train_ratio=0.8)

    assert len(train) > len(test)
    assert len(train) + len(test) == len(df)


def test_job_sequence_disjoint() -> None:
    df = make_project_df(n_jobs=20, tests_per_job=3)
    train, test = temporal_split(df, train_ratio=0.8)

    train_seqs = set(train["job_sequence"].unique())
    test_seqs = set(test["job_sequence"].unique())
    assert train_seqs.isdisjoint(test_seqs)


def test_null_sha_rows_in_both_sets() -> None:
    # NULL-SHA jobs at seq=2 (early) and seq=9 (late), n_jobs=10
    df = make_project_df(n_jobs=10, tests_per_job=2, null_sha_jobs=[2, 9])
    train, test = temporal_split(df, train_ratio=0.8)

    # seq=2 is in the first 80% → train; seq=9 is in last 20% → test
    assert (train["commit_sha"].isna()).any(), "NULL-SHA rows must appear in train"
    assert (test["commit_sha"].isna()).any(), "NULL-SHA rows must appear in test"


def test_all_rows_same_job_stay_together() -> None:
    # job_sequence=5 has two tests — both must end up in the same split
    df = make_project_df(n_jobs=10, tests_per_job=2, null_sha_jobs=[])
    train, test = temporal_split(df, train_ratio=0.8)

    job5_in_train = (train["job_sequence"] == 5).sum()
    job5_in_test = (test["job_sequence"] == 5).sum()
    assert job5_in_train == 0 or job5_in_test == 0, (
        "Rows from job_sequence=5 must not be split across train and test"
    )


def test_small_df_two_jobs() -> None:
    # Edge case: only 2 jobs; train_ratio=0.8 → floor(0.8*2)=1 → seq<=1 train, seq>1 test
    df = make_project_df(n_jobs=2, tests_per_job=2, null_sha_jobs=[])
    train, test = temporal_split(df, train_ratio=0.8)

    assert len(train) > 0
    assert len(test) > 0
    assert set(train["job_sequence"]).isdisjoint(set(test["job_sequence"]))
