"""Feature matrix validation checks for Sprint 2."""

from __future__ import annotations

import pandas as pd

BASELINES = {
    "adamfisk@LittleProxy": {"baseline": 30.42, "type": "relative", "tolerance": 0.01},
    "l0rdn1kk0n@wicket-bootstrap": {"baseline": 19.33, "type": "relative", "tolerance": 0.01},
    "thinkaurelius@titan": {"baseline": 12.91, "type": "relative", "tolerance": 0.01},
    "deeplearning4j@deeplearning4j": {"baseline": 5.70, "type": "relative", "tolerance": 0.01},
    "neuland@jade4j": {"baseline": 0.10, "type": "absolute", "tolerance": 0.5},
}


def validate_features(df: pd.DataFrame) -> None:
    """Raise ``AssertionError`` if the feature matrix violates Sprint 2 gates."""
    assert df.shape[0] > 0, "DataFrame is empty (0 rows)"

    _assert_required_columns(df)
    _assert_null_rates(df)
    _assert_label_values(df)
    _assert_timestamp_monotonic(df)
    _assert_feature_source_values(df)
    _assert_feature_source_ratios(df)
    _assert_feature_count(df)


def _assert_required_columns(df: pd.DataFrame) -> None:
    required = {"repo", "label", "timestamp", "feature_source", "commit_sha", "test_id"}
    missing = required - set(df.columns)
    assert not missing, f"Missing required columns: {sorted(missing)}"


def _assert_null_rates(df: pd.DataFrame) -> None:
    exempt = {"timestamp", "feature_source", "commit_sha", "test_id"}
    for column in df.columns:
        if column in exempt:
            continue
        null_pct = float(df[column].isnull().mean())
        assert null_pct <= 0.05, (
            f"Column '{column}' has {null_pct:.1%} NULL (threshold: 5%)"
        )


def _assert_label_values(df: pd.DataFrame) -> None:
    actual = set(df["label"].dropna().unique())
    unexpected = actual - {0, 1}
    assert not unexpected, f"label column contains unexpected values: {unexpected}"


def _assert_timestamp_monotonic(df: pd.DataFrame) -> None:
    ts_df = df[df["timestamp"].notna()].sort_values(["test_id", "timestamp"])
    if ts_df.empty:
        return
    monotonic = ts_df.groupby("test_id")["timestamp"].apply(lambda series: series.is_monotonic_increasing)
    assert bool(monotonic.all()), (
        "timestamp is not monotonically non-decreasing within at least one test_id group"
    )


def _assert_feature_source_values(df: pd.DataFrame) -> None:
    valid = {"timestamp", "job_sequence"}
    actual = set(df["feature_source"].dropna().unique())
    unexpected = actual - valid
    assert not unexpected, f"feature_source contains unexpected values: {unexpected}"


def _assert_feature_source_ratios(df: pd.DataFrame) -> None:
    for project in sorted(df["repo"].dropna().unique()):
        if project not in BASELINES:
            continue
        config = BASELINES[project]
        observed_pct = float((df[df["repo"] == project]["feature_source"] == "job_sequence").mean() * 100)
        baseline = float(config["baseline"])
        if config["type"] == "relative":
            allowed = baseline * float(config["tolerance"])
            assert abs(observed_pct - baseline) <= allowed, (
                f"{project}: feature_source job_sequence ratio {observed_pct:.2f}% "
                f"vs baseline {baseline:.2f}% (relative +/-1%)"
            )
        else:
            allowed = float(config["tolerance"])
            assert abs(observed_pct - baseline) <= allowed, (
                f"{project}: feature_source job_sequence ratio {observed_pct:.2f}% "
                f"vs baseline {baseline:.2f}% (absolute +/-0.5pp)"
            )


def _assert_feature_count(df: pd.DataFrame) -> None:
    excluded = {"commit_sha", "test_id", "label", "timestamp", "feature_source"}
    feature_cols = [column for column in df.columns if column not in excluded]
    assert len(feature_cols) >= 20, (
        f"Only {len(feature_cols)} feature columns (need >= 20, excluded: {excluded})"
    )
