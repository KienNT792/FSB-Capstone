"""Commit-level feature extraction for Sprint 2."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
from typing import Any

import duckdb
import pandas as pd

RISK_KEYWORDS = [
    "fix",
    "hotfix",
    "bug",
    "patch",
    "revert",
    "urgent",
    "crash",
    "error",
    "broken",
    "regression",
]


class CommitFeatureExtractor:
    """Extract commit churn, metadata, and author-history features."""

    def __init__(self, repo: Any, db_path: str | Path) -> None:
        self.repo = repo
        self.db_path = str(db_path)
        self._diff_unavailable = False

    def extract(self, commit_sha: str) -> dict[str, int]:
        """Return file-list and git metadata features for one commit."""
        features = self._file_change_features(commit_sha)
        features.update(self._empty_metadata(commit_meta_missing=0))

        try:
            commit = self.repo.commit(commit_sha)
        except Exception:
            features.update(self._empty_metadata(commit_meta_missing=1))
            return features

        parents = list(getattr(commit, "parents", []) or [])
        lines_added = 0
        lines_deleted = 0
        commit_diff_missing = 0
        if parents:
            parent_sha = str(getattr(parents[0], "hexsha", parents[0]))
            cli_counts = self._line_counts_from_git_cli(commit_sha, parent_sha)
            if cli_counts is not None:
                lines_added, lines_deleted, commit_diff_missing = cli_counts
            else:
                try:
                    for diff_item in commit.diff(parents[0], create_patch=True):
                        added, deleted = self._count_diff_lines(getattr(diff_item, "diff", b""))
                        lines_added += added
                        lines_deleted += deleted
                except Exception:
                    lines_added = 0
                    lines_deleted = 0
                    commit_diff_missing = 1

        authored_datetime = getattr(commit, "authored_datetime", None)
        if authored_datetime is None:
            authored_datetime = getattr(commit, "committed_datetime", None)

        features.update(
            {
                "lines_added": int(lines_added),
                "lines_deleted": int(lines_deleted),
                "churn_total": int(lines_added + lines_deleted),
                "is_merge_commit": int(len(parents) > 1),
                "commit_hour": self._datetime_part(authored_datetime, "hour"),
                "commit_day_of_week": self._datetime_part(authored_datetime, "weekday"),
                "keyword_risk_score": self._keyword_risk_score(
                    str(getattr(commit, "message", "") or "")
                ),
                "commit_meta_missing": 0,
                "commit_diff_missing": commit_diff_missing,
            }
        )
        return features

    def extract_author_features(
        self, commit_sha: str | None, history_df: pd.DataFrame
    ) -> dict[str, int | float | str]:
        """Return author history using only records strictly before this commit.

        ``history_df`` must include an ``author_email`` column. FeatureJoiner is
        responsible for resolving that value from git metadata before calling
        this method because it is not stored in ``test_runs``.
        """
        base = {
            "author_commit_count_90d": 0,
            "author_failure_rate_90d": -1.0,
            "author_feature_fallback": 1,
            "feature_source": "job_sequence",
        }
        if history_df.empty or not commit_sha or "commit_sha" not in history_df.columns:
            return base

        current_rows = history_df[history_df["commit_sha"] == commit_sha]
        if current_rows.empty:
            return base

        current = current_rows.iloc[0]
        current_ts = self._nullable_number(current.get("timestamp"))
        current_sequence = self._nullable_number(current.get("job_sequence"))
        author_email = str(current.get("author_email") or "")
        if not author_email:
            author_email = self._author_email_from_git(commit_sha)
        if not author_email:
            return base

        # Keep fallback row-scoped so FeatureJoiner can satisfy the Sprint 2
        # audit invariant: feature_source='job_sequence' tracks null commit SHAs.
        use_fallback = current_ts is None

        if use_fallback:
            if current_sequence is None or "job_sequence" not in history_df.columns:
                return base
            author_values = history_df.get("author_email", pd.Series("", index=history_df.index))
            window = history_df[
                (author_values.fillna("") == author_email)
                & (pd.to_numeric(history_df["job_sequence"], errors="coerce") < current_sequence)
            ].copy()
            source = "job_sequence"
            fallback = 1
        else:
            lower_bound = current_ts - 90 * 86400
            ts_values = pd.to_numeric(history_df["timestamp"], errors="coerce")
            author_values = history_df.get("author_email", pd.Series("", index=history_df.index))
            window = history_df[
                (author_values.fillna("") == author_email)
                & (ts_values < current_ts)
                & (ts_values >= lower_bound)
            ].copy()
            source = "timestamp"
            fallback = 0

        commit_summary = self._author_commit_summary(window)
        count = int(len(commit_summary))
        if count < 3:
            failure_rate = -1.0
        else:
            failure_rate = float(commit_summary["failed"].mean())

        return {
            "author_commit_count_90d": count,
            "author_failure_rate_90d": failure_rate,
            "author_feature_fallback": fallback,
            "feature_source": source,
        }

    def _file_change_features(self, commit_sha: str) -> dict[str, int]:
        with duckdb.connect(self.db_path, read_only=True) as con:
            columns = {
                row[0]
                for row in con.execute("DESCRIBE file_changes").fetchall()
            }
            path_column = "file_path" if "file_path" in columns else "filepath"
            rows = con.execute(
                f"SELECT {path_column} FROM file_changes WHERE commit_sha = ?",
                [commit_sha],
            ).fetchall()

        paths = [str(row[0] or "") for row in rows]
        java_paths = [path for path in paths if path.lower().endswith(".java")]
        test_paths = [path for path in java_paths if self._is_test_path(path)]
        return {
            "files_changed_total": int(len(paths)),
            "java_files_changed": int(len(java_paths)),
            "source_files_changed": int(len(java_paths) - len(test_paths)),
            "test_files_changed": int(len(test_paths)),
        }

    @staticmethod
    def _is_test_path(path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return "/test/" in normalized or normalized.startswith("test/")

    @staticmethod
    def _empty_metadata(commit_meta_missing: int) -> dict[str, int]:
        return {
            "lines_added": 0,
            "lines_deleted": 0,
            "churn_total": 0,
            "is_merge_commit": 0,
            "commit_hour": 0,
            "commit_day_of_week": 0,
            "keyword_risk_score": 0,
            "commit_meta_missing": int(commit_meta_missing),
            "commit_diff_missing": int(commit_meta_missing),
        }

    @staticmethod
    def _count_diff_lines(diff: bytes | str | None) -> tuple[int, int]:
        if diff is None:
            return 0, 0
        if isinstance(diff, bytes):
            text = diff.decode("utf-8", errors="ignore")
        else:
            text = str(diff)

        added = 0
        deleted = 0
        for line in text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                deleted += 1
        return added, deleted

    def _line_counts_from_git_cli(self, commit_sha: str, parent_sha: str) -> tuple[int, int, int] | None:
        repo_path = getattr(self.repo, "working_tree_dir", None) or getattr(self.repo, "git_dir", None)
        if not repo_path or not isinstance(repo_path, (str, Path)):
            return None
        if self._diff_unavailable:
            return 0, 0, 1
        env = os.environ.copy()
        env["GIT_NO_LAZY_FETCH"] = "1"
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat", parent_sha, commit_sha],
                cwd=str(repo_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception:
            self._diff_unavailable = True
            return 0, 0, 1
        if result.returncode != 0:
            if self._is_blobless_diff_error(result.stderr):
                self._diff_unavailable = True
            return 0, 0, 1

        added = 0
        deleted = 0
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2 or parts[0] == "-" or parts[1] == "-":
                continue
            try:
                added += int(parts[0])
                deleted += int(parts[1])
            except ValueError:
                continue
        return added, deleted, 0

    @staticmethod
    def _is_blobless_diff_error(stderr: str) -> bool:
        lowered = (stderr or "").lower()
        return any(
            marker in lowered
            for marker in (
                "could not fetch",
                "failed to connect",
                "unable to access",
                "missing blob",
                "promisor",
            )
        )

    @staticmethod
    def _datetime_part(value: Any, part: str) -> int:
        if value is None:
            return 0
        if isinstance(value, pd.Timestamp):
            value = value.to_pydatetime()
        if isinstance(value, datetime):
            return int(value.hour if part == "hour" else value.weekday())
        return 0

    @staticmethod
    def _keyword_risk_score(message: str) -> int:
        lowered = message.lower()
        return sum(
            1
            for keyword in RISK_KEYWORDS
            if re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", lowered)
        )

    @staticmethod
    def _nullable_number(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _author_email_from_git(self, commit_sha: str) -> str:
        try:
            commit = self.repo.commit(commit_sha)
            return str(getattr(getattr(commit, "author", None), "email", "") or "")
        except Exception:
            return ""

    @staticmethod
    def _author_commit_summary(window: pd.DataFrame) -> pd.DataFrame:
        if window.empty:
            return pd.DataFrame(columns=["commit_sha", "failed"])

        work = window.copy()
        if "commit_sha" not in work.columns:
            work["commit_sha"] = range(len(work))
        if "job_id" in work.columns:
            fallback_key = work["job_id"]
        else:
            fallback_key = pd.Series(work.index, index=work.index)
        work["commit_key"] = work["commit_sha"].where(work["commit_sha"].notna(), fallback_key)
        work["failed"] = work["outcome"].isin(["FAIL", "ERROR"]).astype(int)
        return (
            work.groupby("commit_key", dropna=False)["failed"]
            .max()
            .reset_index()
            .rename(columns={"commit_key": "commit_sha"})
        )
