"""Per-test history feature extraction for Sprint 2."""

from __future__ import annotations

import pandas as pd

SECONDS_PER_DAY = 86400


class TestHistoryFeatureExtractor:
    """Extract rolling history features for one test before an as-of point."""

    COLD_START = {
        "last_outcome": -1,
        "failure_rate_7d": -1.0,
        "failure_rate_30d": -1.0,
        "failure_rate_90d": -1.0,
        "days_since_last_fail": 999.0,
        "days_since_last_run": 999.0,
        "consecutive_passes": 0,
        "avg_duration_ms": 0.0,
        "duration_variance": 0.0,
        "run_count_30d": 0,
    }

    def extract(
        self, test_id: str, as_of_ts: int | float, history_df: pd.DataFrame
    ) -> dict[str, int | float]:
        """Return rolling features from records strictly before ``as_of_ts``."""
        if history_df.empty:
            return dict(self.COLD_START)

        work = history_df[history_df["test_id"] == test_id].copy()
        if work.empty:
            return dict(self.COLD_START)

        work["effective_ts"] = self._effective_timestamp(work)
        work = work[pd.to_numeric(work["effective_ts"], errors="coerce") < float(as_of_ts)]
        if work.empty:
            return dict(self.COLD_START)

        work["is_failure"] = work["outcome"].isin(["FAIL", "ERROR"]).astype(int)
        work = work.sort_values(["effective_ts", "job_sequence"], ascending=[False, False])

        recent = work.iloc[0]
        last_outcome = int(recent["is_failure"])
        days_since_last_run = max(0.0, (float(as_of_ts) - float(recent["effective_ts"])) / SECONDS_PER_DAY)

        fail_rows = work[work["is_failure"] == 1]
        if fail_rows.empty:
            days_since_last_fail = 999.0
        else:
            last_fail_ts = float(fail_rows.iloc[0]["effective_ts"])
            days_since_last_fail = max(0.0, (float(as_of_ts) - last_fail_ts) / SECONDS_PER_DAY)

        consecutive_passes = 0
        for _, row in work.iterrows():
            if int(row["is_failure"]) == 0:
                consecutive_passes += 1
            else:
                break

        last_20 = work.head(20)
        durations = pd.to_numeric(last_20.get("duration_ms"), errors="coerce").dropna()
        avg_duration = float(durations.mean()) if not durations.empty else 0.0
        duration_variance = float(durations.var(ddof=0)) if len(durations) >= 2 else 0.0

        return {
            "last_outcome": last_outcome,
            "failure_rate_7d": self._failure_rate(work, as_of_ts, 7),
            "failure_rate_30d": self._failure_rate(work, as_of_ts, 30),
            "failure_rate_90d": self._failure_rate(work, as_of_ts, 90),
            "days_since_last_fail": days_since_last_fail,
            "days_since_last_run": days_since_last_run,
            "consecutive_passes": int(consecutive_passes),
            "avg_duration_ms": avg_duration,
            "duration_variance": duration_variance,
            "run_count_30d": int(self._window(work, as_of_ts, 30).shape[0]),
        }

    @staticmethod
    def _effective_timestamp(df: pd.DataFrame) -> pd.Series:
        timestamp = pd.to_numeric(df.get("timestamp"), errors="coerce")
        sequence = pd.to_numeric(df.get("job_sequence"), errors="coerce")
        pseudo_ts = sequence * SECONDS_PER_DAY
        return timestamp.where(timestamp.notna(), pseudo_ts)

    @classmethod
    def _window(cls, df: pd.DataFrame, as_of_ts: int | float, days: int) -> pd.DataFrame:
        lower = float(as_of_ts) - days * SECONDS_PER_DAY
        ts_values = pd.to_numeric(df["effective_ts"], errors="coerce")
        return df[(ts_values >= lower) & (ts_values < float(as_of_ts))]

    @classmethod
    def _failure_rate(cls, df: pd.DataFrame, as_of_ts: int | float, days: int) -> float:
        window = cls._window(df, as_of_ts, days)
        if window.empty:
            return -1.0
        return float(window["is_failure"].mean())
