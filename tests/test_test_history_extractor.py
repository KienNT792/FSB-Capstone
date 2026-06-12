from __future__ import annotations

import pandas as pd

from src.features.test_history_extractor import SECONDS_PER_DAY, TestHistoryFeatureExtractor


def rows(records: list[dict]) -> pd.DataFrame:
    defaults = {
        "test_id": "com.example.FooTest",
        "outcome": "PASS",
        "timestamp": 0,
        "job_sequence": 0,
        "job_id": "0",
        "duration_ms": 10.0,
    }
    return pd.DataFrame([{**defaults, **record} for record in records])


def test_cold_start_returns_sentinels() -> None:
    result = TestHistoryFeatureExtractor().extract("missing", 1000, rows([]))

    assert result == TestHistoryFeatureExtractor.COLD_START


def test_no_prior_history_for_test_returns_sentinels() -> None:
    history = rows([{"test_id": "other.Test", "timestamp": 100}])

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 200, history)

    assert result["last_outcome"] == -1
    assert result["days_since_last_fail"] == 999.0


def test_only_failures_sets_last_outcome_and_zero_consecutive_passes() -> None:
    history = rows(
        [
            {"outcome": "FAIL", "timestamp": 100, "job_sequence": 1},
            {"outcome": "ERROR", "timestamp": 200, "job_sequence": 2},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 300, history)

    assert result["last_outcome"] == 1
    assert result["consecutive_passes"] == 0
    assert result["failure_rate_30d"] == 1.0


def test_only_passes_counts_consecutive_passes_and_never_failed() -> None:
    history = rows(
        [
            {"outcome": "PASS", "timestamp": 100, "job_sequence": 1},
            {"outcome": "SKIPPED", "timestamp": 200, "job_sequence": 2},
            {"outcome": "PASS", "timestamp": 300, "job_sequence": 3},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 400, history)

    assert result["last_outcome"] == 0
    assert result["consecutive_passes"] == 3
    assert result["days_since_last_fail"] == 999.0
    assert result["failure_rate_30d"] == 0.0


def test_mixed_history_computes_failure_rate_30d() -> None:
    as_of = 100 * SECONDS_PER_DAY
    history = rows(
        [
            {"outcome": "PASS", "timestamp": as_of - 3 * SECONDS_PER_DAY, "job_sequence": 1},
            {"outcome": "FAIL", "timestamp": as_of - 2 * SECONDS_PER_DAY, "job_sequence": 2},
            {"outcome": "PASS", "timestamp": as_of - 1 * SECONDS_PER_DAY, "job_sequence": 3},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", as_of, history)

    assert result["failure_rate_30d"] == 1 / 3
    assert result["last_outcome"] == 0
    assert result["consecutive_passes"] == 1


def test_record_at_exact_as_of_is_excluded() -> None:
    history = rows(
        [
            {"outcome": "PASS", "timestamp": 100, "job_sequence": 1},
            {"outcome": "FAIL", "timestamp": 200, "job_sequence": 2},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 200, history)

    assert result["last_outcome"] == 0
    assert result["failure_rate_30d"] == 0.0


def test_90_day_window_boundary_is_inclusive_at_lower_bound() -> None:
    as_of = 200 * SECONDS_PER_DAY
    history = rows(
        [
            {"outcome": "FAIL", "timestamp": as_of - 90 * SECONDS_PER_DAY - 1, "job_sequence": 1},
            {"outcome": "PASS", "timestamp": as_of - 90 * SECONDS_PER_DAY, "job_sequence": 2},
            {"outcome": "FAIL", "timestamp": as_of - 1, "job_sequence": 3},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", as_of, history)

    assert result["failure_rate_90d"] == 0.5


def test_duration_variance_is_zero_with_one_prior_record() -> None:
    history = rows([{"outcome": "PASS", "timestamp": 100, "duration_ms": 42.0}])

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 200, history)

    assert result["avg_duration_ms"] == 42.0
    assert result["duration_variance"] == 0.0


def test_duration_variance_uses_last_20_runs() -> None:
    history = rows(
        [
            {"timestamp": i * 10, "job_sequence": i, "duration_ms": float(i)}
            for i in range(1, 23)
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", 230, history)

    assert result["avg_duration_ms"] == 12.5
    assert result["duration_variance"] == 33.25


def test_run_count_30d_counts_only_window_rows() -> None:
    as_of = 100 * SECONDS_PER_DAY
    history = rows(
        [
            {"timestamp": as_of - 31 * SECONDS_PER_DAY, "job_sequence": 1},
            {"timestamp": as_of - 30 * SECONDS_PER_DAY, "job_sequence": 2},
            {"timestamp": as_of - 1, "job_sequence": 3},
        ]
    )

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", as_of, history)

    assert result["run_count_30d"] == 2


def test_null_timestamp_rows_use_job_sequence_pseudo_timestamp() -> None:
    history = rows(
        [
            {"outcome": "PASS", "timestamp": None, "job_sequence": 1},
            {"outcome": "FAIL", "timestamp": None, "job_sequence": 2},
            {"outcome": "PASS", "timestamp": None, "job_sequence": 3},
        ]
    )
    as_of = 3 * SECONDS_PER_DAY

    result = TestHistoryFeatureExtractor().extract("com.example.FooTest", as_of, history)

    assert result["last_outcome"] == 1
    assert result["run_count_30d"] == 2
    assert result["failure_rate_30d"] == 0.5
