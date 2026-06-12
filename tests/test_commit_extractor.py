from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import duckdb
import pandas as pd

from src.features.commit_extractor import CommitFeatureExtractor


class DiffItem:
    def __init__(self, diff: bytes) -> None:
        self.diff = diff


def make_db(tmp_path: Path, rows: list[tuple[str, str, str]]) -> Path:
    db_path = tmp_path / "features.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE file_changes (
            repo VARCHAR,
            commit_sha VARCHAR,
            file_path VARCHAR
        )
        """
    )
    if rows:
        con.executemany("INSERT INTO file_changes VALUES (?, ?, ?)", rows)
    con.close()
    return db_path


def make_commit(
    *,
    parents: list[object] | None = None,
    diff_items: list[DiffItem] | None = None,
    message: str = "regular change",
    authored: datetime | None = None,
    author_email: str = "dev@example.com",
) -> MagicMock:
    commit = MagicMock()
    commit.parents = parents if parents is not None else [object()]
    commit.diff.return_value = diff_items if diff_items is not None else []
    commit.message = message
    commit.authored_datetime = authored or datetime(2024, 1, 3, 10, tzinfo=timezone.utc)
    commit.author = SimpleNamespace(email=author_email)
    return commit


def extractor(tmp_path: Path, rows: list[tuple[str, str, str]], commit: object) -> CommitFeatureExtractor:
    repo = MagicMock()
    repo.commit.return_value = commit
    return CommitFeatureExtractor(repo=repo, db_path=make_db(tmp_path, rows))


def test_normal_commit_extracts_file_and_metadata_features(tmp_path: Path) -> None:
    commit = make_commit(
        diff_items=[
            DiffItem(b"+++ b/A.java\n--- a/A.java\n+new line\n-old line\n context\n"),
            DiffItem(b"+another\n-delete this\n"),
        ],
        authored=datetime(2024, 1, 3, 10, tzinfo=timezone.utc),
    )
    subject = extractor(
        tmp_path,
        [
            ("repo", "abc", "src/main/java/A.java"),
            ("repo", "abc", "src/test/java/ATest.java"),
            ("repo", "abc", "README.md"),
        ],
        commit,
    )

    result = subject.extract("abc")

    assert result["files_changed_total"] == 3
    assert result["java_files_changed"] == 2
    assert result["source_files_changed"] == 1
    assert result["test_files_changed"] == 1
    assert result["lines_added"] == 2
    assert result["lines_deleted"] == 2
    assert result["churn_total"] == 4
    assert result["commit_hour"] == 10
    assert result["commit_day_of_week"] == 2
    assert result["commit_meta_missing"] == 0


def test_merge_commit_sets_merge_flag_and_uses_first_parent(tmp_path: Path) -> None:
    first_parent = object()
    commit = make_commit(parents=[first_parent, object()], diff_items=[DiffItem(b"+x\n")])
    subject = extractor(tmp_path, [("repo", "merge", "src/main/java/A.java")], commit)

    result = subject.extract("merge")

    assert result["is_merge_commit"] == 1
    commit.diff.assert_called_once_with(first_parent, create_patch=True)


def test_initial_commit_zeroes_diff_features(tmp_path: Path) -> None:
    commit = make_commit(parents=[])
    subject = extractor(tmp_path, [("repo", "init", "src/main/java/A.java")], commit)

    result = subject.extract("init")

    assert result["lines_added"] == 0
    assert result["lines_deleted"] == 0
    assert result["churn_total"] == 0
    commit.diff.assert_not_called()


def test_missing_commit_returns_file_features_and_missing_metadata_flag(tmp_path: Path) -> None:
    repo = MagicMock()
    repo.commit.side_effect = ValueError("missing commit")
    subject = CommitFeatureExtractor(
        repo=repo,
        db_path=make_db(tmp_path, [("repo", "missing", "src/main/java/A.java")]),
    )

    result = subject.extract("missing")

    assert result["files_changed_total"] == 1
    assert result["java_files_changed"] == 1
    assert result["lines_added"] == 0
    assert result["commit_meta_missing"] == 1


def test_commit_with_no_java_files_returns_zero_java_counts(tmp_path: Path) -> None:
    commit = make_commit(diff_items=[DiffItem(b"+doc\n")])
    subject = extractor(tmp_path, [("repo", "docs", "README.md")], commit)

    result = subject.extract("docs")

    assert result["files_changed_total"] == 1
    assert result["java_files_changed"] == 0
    assert result["source_files_changed"] == 0
    assert result["test_files_changed"] == 0


def test_keyword_risk_score_counts_exact_keyword_list(tmp_path: Path) -> None:
    commit = make_commit(message="Hotfix for runtime error")
    subject = extractor(tmp_path, [("repo", "risk", "src/main/java/A.java")], commit)

    result = subject.extract("risk")

    assert result["keyword_risk_score"] == 2


def test_test_path_detection_is_case_insensitive_and_slash_normalized(tmp_path: Path) -> None:
    commit = make_commit()
    subject = extractor(
        tmp_path,
        [
            ("repo", "paths", r"module\src\test\java\ATest.java"),
            ("repo", "paths", "src/main/java/A.java"),
        ],
        commit,
    )

    result = subject.extract("paths")

    assert result["java_files_changed"] == 2
    assert result["test_files_changed"] == 1
    assert result["source_files_changed"] == 1


def test_author_features_timestamp_path_excludes_future_and_current_commit(tmp_path: Path) -> None:
    subject = extractor(tmp_path, [], make_commit())
    now = 1_700_000_000
    history = pd.DataFrame(
        [
            {"commit_sha": "old1", "outcome": "PASS", "timestamp": now - 3, "job_sequence": 1, "author_email": "a@x"},
            {"commit_sha": "old2", "outcome": "FAIL", "timestamp": now - 2, "job_sequence": 2, "author_email": "a@x"},
            {"commit_sha": "old3", "outcome": "PASS", "timestamp": now - 1, "job_sequence": 3, "author_email": "a@x"},
            {"commit_sha": "cur", "outcome": "FAIL", "timestamp": now, "job_sequence": 4, "author_email": "a@x"},
            {"commit_sha": "future", "outcome": "FAIL", "timestamp": now + 1, "job_sequence": 5, "author_email": "a@x"},
        ]
    )

    result = subject.extract_author_features("cur", history)

    assert result["feature_source"] == "timestamp"
    assert result["author_feature_fallback"] == 0
    assert result["author_commit_count_90d"] == 3
    assert result["author_failure_rate_90d"] == 1 / 3


def test_author_features_fallback_uses_prior_job_sequence_when_current_timestamp_null(tmp_path: Path) -> None:
    subject = extractor(tmp_path, [], make_commit())
    history = pd.DataFrame(
        [
            {"commit_sha": "old1", "outcome": "PASS", "timestamp": None, "job_sequence": 1, "author_email": "a@x"},
            {"commit_sha": "old2", "outcome": "ERROR", "timestamp": None, "job_sequence": 2, "author_email": "a@x"},
            {"commit_sha": "old3", "outcome": "PASS", "timestamp": None, "job_sequence": 3, "author_email": "a@x"},
            {"commit_sha": "cur", "outcome": "PASS", "timestamp": None, "job_sequence": 4, "author_email": "a@x"},
            {"commit_sha": "future", "outcome": "FAIL", "timestamp": None, "job_sequence": 5, "author_email": "a@x"},
        ]
    )

    result = subject.extract_author_features("cur", history)

    assert result["feature_source"] == "job_sequence"
    assert result["author_feature_fallback"] == 1
    assert result["author_commit_count_90d"] == 3
    assert result["author_failure_rate_90d"] == 1 / 3


def test_author_features_unseen_author_returns_negative_rate(tmp_path: Path) -> None:
    subject = extractor(tmp_path, [], make_commit())
    history = pd.DataFrame(
        [
            {"commit_sha": "old1", "outcome": "FAIL", "timestamp": 100, "job_sequence": 1, "author_email": "a@x"},
            {"commit_sha": "cur", "outcome": "PASS", "timestamp": 200, "job_sequence": 2, "author_email": "a@x"},
        ]
    )

    result = subject.extract_author_features("cur", history)

    assert result["author_commit_count_90d"] == 1
    assert result["author_failure_rate_90d"] == -1.0
