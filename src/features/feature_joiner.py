"""Assemble Sprint 2 feature rows from extractor blocks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

try:
    import git
except Exception:  # pragma: no cover - import failure is handled at runtime.
    git = None

from src.features.commit_extractor import CommitFeatureExtractor
from src.features.dependency_extractor import DependencyFeatureExtractor
from src.features.test_history_extractor import SECONDS_PER_DAY, TestHistoryFeatureExtractor


class MissingRepo:
    """Repo shim that makes git metadata features degrade to missing."""

    def commit(self, _sha: str) -> Any:
        raise ValueError("git repository unavailable")


class FeatureJoiner:
    """Build a feature DataFrame for one RTPTorrent project."""

    SENTINEL_ALLOWED_NULLS = {"timestamp", "commit_sha"}

    def __init__(
        self,
        git_root: str | Path = "data/git-repos",
        output_dir: str | Path = "data/features",
        commit_extractor: Any | None = None,
        test_history_extractor: Any | None = None,
        dependency_extractor: Any | None = None,
    ) -> None:
        self.git_root = Path(git_root)
        self.output_dir = Path(output_dir)
        self.commit_extractor = commit_extractor
        self.use_precomputed_history = test_history_extractor is None
        self.test_history_extractor = test_history_extractor or TestHistoryFeatureExtractor()
        self.dependency_extractor = dependency_extractor or DependencyFeatureExtractor()

    def build(self, repo: str, db_path: str | Path) -> pd.DataFrame:
        """Build and save one row per test run for ``repo``."""
        history_df, changes_df = self._load_project_frames(repo, db_path)
        if history_df.empty:
            raise ValueError(f"No test_runs rows found for repo: {repo}")
        if isinstance(self.dependency_extractor, DependencyFeatureExtractor):
            self.dependency_extractor.add_observed_test_source_paths(changes_df["file_path"])

        git_repo = self._open_git_repo(repo)
        history_df = history_df.copy()
        history_df["author_email"] = self._resolve_author_emails(git_repo, history_df)

        commit_extractor = self.commit_extractor or CommitFeatureExtractor(git_repo, db_path)
        rows: list[dict[str, Any]] = []
        commit_feature_cache: dict[str | None, dict[str, Any]] = {}
        author_feature_cache: dict[str | None, dict[str, Any]] = {}
        dependency_cache: dict[tuple[str, str | None], dict[str, Any]] = {}
        change_cache = self._changed_files_by_commit(changes_df)
        history_by_test = {
            str(test_id): group.copy()
            for test_id, group in history_df.groupby("test_id", sort=False)
        }
        precomputed_history = (
            self._precompute_test_history_features(history_df)
            if self.use_precomputed_history
            else {}
        )

        ordered = self._ordered_history(history_df)
        unique_commits = list(dict.fromkeys(ordered["commit_sha"].where(ordered["commit_sha"].notna(), None)))
        total_commits = len(unique_commits)

        for index, commit_sha in enumerate(unique_commits, start=1):
            if index == 1 or index % 10 == 0:
                label = "NULL" if commit_sha is None else str(commit_sha)[:8]
                print(f"Processing commit {index}/{total_commits}: {label}")

            commit_rows = ordered[
                ordered["commit_sha"].isna()
                if commit_sha is None
                else ordered["commit_sha"] == commit_sha
            ]
            commit_features = self._commit_features(commit_extractor, commit_sha, commit_feature_cache)
            author_features = self._author_features(
                commit_extractor, commit_sha, history_df, author_feature_cache
            )
            changed_java_files = change_cache.get(commit_sha, [])

            for _, run in commit_rows.iterrows():
                test_id = str(run["test_id"])
                as_of_ts = self._as_of_timestamp(run)
                if self.use_precomputed_history:
                    test_features = precomputed_history[int(run.name)]
                else:
                    test_features = self.test_history_extractor.extract(
                        test_id, as_of_ts, history_by_test.get(test_id, history_df.iloc[0:0])
                    )
                dependency_features = self._dependency_features(
                    test_id,
                    commit_sha,
                    changed_java_files,
                    self.git_root / repo,
                    dependency_cache,
                )

                row = {
                    "repo": repo,
                    "commit_sha": None if pd.isna(run["commit_sha"]) else run["commit_sha"],
                    "test_id": test_id,
                    "label": self._label(run["outcome"]),
                    "timestamp": run["timestamp"],
                    **commit_features,
                    **author_features,
                    **test_features,
                    **dependency_features,
                }
                rows.append(row)

        df = pd.DataFrame(rows)
        self._raise_on_unexpected_nulls(df)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.output_dir / f"{repo}_features.parquet", index=False)
        return df

    @staticmethod
    def _load_project_frames(repo: str, db_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        with duckdb.connect(str(db_path), read_only=True) as con:
            history_df = con.execute(
                """
                SELECT repo, job_id, commit_sha, test_id, outcome, timestamp,
                       job_sequence, duration_ms
                FROM test_runs
                WHERE repo = ?
                """,
                [repo],
            ).df()
            changes_df = con.execute(
                "SELECT repo, commit_sha, file_path FROM file_changes WHERE repo = ?",
                [repo],
            ).df()
        return history_df, changes_df

    def _open_git_repo(self, repo: str) -> Any:
        repo_path = self.git_root / repo
        if git is None or not repo_path.exists():
            return MissingRepo()
        try:
            self._add_process_safe_directory(repo_path)
            return git.Repo(repo_path)
        except Exception:
            return MissingRepo()

    @staticmethod
    def _add_process_safe_directory(repo_path: Path) -> None:
        safe_path = repo_path.resolve().as_posix()
        existing_count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
        for index in range(existing_count):
            key = os.environ.get(f"GIT_CONFIG_KEY_{index}")
            value = os.environ.get(f"GIT_CONFIG_VALUE_{index}")
            if key == "safe.directory" and value == safe_path:
                return
        os.environ["GIT_CONFIG_COUNT"] = str(existing_count + 1)
        os.environ[f"GIT_CONFIG_KEY_{existing_count}"] = "safe.directory"
        os.environ[f"GIT_CONFIG_VALUE_{existing_count}"] = safe_path

    @staticmethod
    def _resolve_author_emails(repo: Any, history_df: pd.DataFrame) -> pd.Series:
        author_map: dict[str, str] = {}
        for sha in history_df["commit_sha"].dropna().unique():
            try:
                author_map[str(sha)] = str(repo.commit(str(sha)).author.email or "")
            except Exception:
                author_map[str(sha)] = ""
        return history_df["commit_sha"].map(lambda sha: "" if pd.isna(sha) else author_map.get(str(sha), ""))

    @staticmethod
    def _changed_files_by_commit(changes_df: pd.DataFrame) -> dict[str, list[str]]:
        if changes_df.empty:
            return {}
        grouped = changes_df.groupby("commit_sha")["file_path"].apply(list)
        return {str(sha): [str(path) for path in paths] for sha, paths in grouped.items()}

    @staticmethod
    def _ordered_history(history_df: pd.DataFrame) -> pd.DataFrame:
        work = history_df.copy()
        timestamp = pd.to_numeric(work["timestamp"], errors="coerce")
        sequence = pd.to_numeric(work["job_sequence"], errors="coerce")
        work["sort_ts"] = timestamp.where(timestamp.notna(), sequence * SECONDS_PER_DAY)
        return work.sort_values(["sort_ts", "job_sequence", "commit_sha", "test_id"], na_position="last")

    @staticmethod
    def _commit_features(
        extractor: Any,
        commit_sha: str | None,
        cache: dict[str | None, dict[str, Any]],
    ) -> dict[str, Any]:
        if commit_sha in cache:
            return cache[commit_sha]
        if commit_sha is None:
            features = {
                "files_changed_total": 0,
                "java_files_changed": 0,
                "source_files_changed": 0,
                "test_files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "churn_total": 0,
                "is_merge_commit": 0,
                "commit_hour": 0,
                "commit_day_of_week": 0,
                "keyword_risk_score": 0,
                "commit_meta_missing": 1,
                "commit_diff_missing": 1,
            }
        else:
            features = dict(extractor.extract(str(commit_sha)))
        cache[commit_sha] = features
        return features

    @staticmethod
    def _author_features(
        extractor: Any,
        commit_sha: str | None,
        history_df: pd.DataFrame,
        cache: dict[str | None, dict[str, Any]],
    ) -> dict[str, Any]:
        if commit_sha not in cache:
            cache[commit_sha] = dict(extractor.extract_author_features(commit_sha, history_df))
        return cache[commit_sha]

    def _dependency_features(
        self,
        test_id: str,
        commit_sha: str | None,
        changed_java_files: list[str],
        repo_path: Path,
        cache: dict[tuple[str, str | None], dict[str, Any]],
    ) -> dict[str, Any]:
        key = (test_id, commit_sha)
        if key not in cache:
            cache[key] = dict(
                self.dependency_extractor.extract(
                    test_id,
                    changed_java_files,
                    repo_path,
                    commit_sha=commit_sha,
                )
            )
        return cache[key]

    @staticmethod
    def _as_of_timestamp(run: pd.Series) -> float:
        if pd.notna(run["timestamp"]):
            return float(run["timestamp"])
        return float(run["job_sequence"]) * SECONDS_PER_DAY

    @classmethod
    def _precompute_test_history_features(cls, history_df: pd.DataFrame) -> dict[int, dict[str, Any]]:
        work = history_df.copy()
        timestamp = pd.to_numeric(work["timestamp"], errors="coerce")
        sequence = pd.to_numeric(work["job_sequence"], errors="coerce")
        work["effective_ts"] = timestamp.where(timestamp.notna(), sequence * SECONDS_PER_DAY)
        work["is_failure"] = work["outcome"].isin(["FAIL", "ERROR"]).astype(int)

        features: dict[int, dict[str, Any]] = {}
        for _, group in work.groupby("test_id", sort=False):
            ordered = group.sort_values(["effective_ts", "job_sequence"])
            prior: list[tuple[float, int, float]] = []
            pass_streak = 0

            for effective_ts, block in ordered.groupby("effective_ts", sort=True):
                ts = float(effective_ts)
                block_features = cls._history_features_from_prior(prior, pass_streak, ts)
                for row_index in block.index:
                    features[int(row_index)] = dict(block_features)

                for _, row in block.sort_values("job_sequence").iterrows():
                    outcome = int(row["is_failure"])
                    duration = row["duration_ms"]
                    duration_value = float(duration) if pd.notna(duration) else float("nan")
                    prior.append((ts, outcome, duration_value))
                    pass_streak = 0 if outcome == 1 else pass_streak + 1

        return features

    @staticmethod
    def _history_features_from_prior(
        prior: list[tuple[float, int, float]], pass_streak: int, as_of_ts: float
    ) -> dict[str, Any]:
        if not prior:
            return dict(TestHistoryFeatureExtractor.COLD_START)

        last_ts, last_failure, _ = prior[-1]
        fail_timestamps = [ts for ts, is_failure, _ in prior if is_failure == 1]
        last_fail_ts = fail_timestamps[-1] if fail_timestamps else None

        last_20_durations = [
            duration
            for _, _, duration in prior[-20:]
            if pd.notna(duration)
        ]
        avg_duration = (
            float(pd.Series(last_20_durations).mean()) if last_20_durations else 0.0
        )
        duration_variance = (
            float(pd.Series(last_20_durations).var(ddof=0))
            if len(last_20_durations) >= 2
            else 0.0
        )

        return {
            "last_outcome": int(last_failure),
            "failure_rate_7d": FeatureJoiner._prior_failure_rate(prior, as_of_ts, 7),
            "failure_rate_30d": FeatureJoiner._prior_failure_rate(prior, as_of_ts, 30),
            "failure_rate_90d": FeatureJoiner._prior_failure_rate(prior, as_of_ts, 90),
            "days_since_last_fail": (
                999.0
                if last_fail_ts is None
                else max(0.0, (as_of_ts - last_fail_ts) / SECONDS_PER_DAY)
            ),
            "days_since_last_run": max(0.0, (as_of_ts - last_ts) / SECONDS_PER_DAY),
            "consecutive_passes": int(pass_streak),
            "avg_duration_ms": avg_duration,
            "duration_variance": duration_variance,
            "run_count_30d": FeatureJoiner._prior_window_count(prior, as_of_ts, 30),
        }

    @staticmethod
    def _prior_window(
        prior: list[tuple[float, int, float]], as_of_ts: float, days: int
    ) -> list[tuple[float, int, float]]:
        lower = as_of_ts - days * SECONDS_PER_DAY
        return [row for row in prior if lower <= row[0] < as_of_ts]

    @classmethod
    def _prior_failure_rate(
        cls, prior: list[tuple[float, int, float]], as_of_ts: float, days: int
    ) -> float:
        window = cls._prior_window(prior, as_of_ts, days)
        if not window:
            return -1.0
        return float(sum(row[1] for row in window) / len(window))

    @classmethod
    def _prior_window_count(
        cls, prior: list[tuple[float, int, float]], as_of_ts: float, days: int
    ) -> int:
        return len(cls._prior_window(prior, as_of_ts, days))

    @staticmethod
    def _label(outcome: str) -> int:
        return int(outcome in {"FAIL", "ERROR"})

    def _raise_on_unexpected_nulls(self, df: pd.DataFrame) -> None:
        null_columns = [
            column
            for column in df.columns
            if column not in self.SENTINEL_ALLOWED_NULLS and df[column].isna().any()
        ]
        if null_columns:
            details = {column: int(df[column].isna().sum()) for column in null_columns}
            raise ValueError(f"Unexpected NULL feature values: {details}")
