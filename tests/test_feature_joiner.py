from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.features.feature_joiner import FeatureJoiner


class FakeCommitExtractor:
    def __init__(self) -> None:
        self.extract_calls: list[str] = []

    def extract(self, commit_sha: str) -> dict:
        self.extract_calls.append(commit_sha)
        index = int(commit_sha[-1])
        return {
            "files_changed_total": index,
            "java_files_changed": index,
            "source_files_changed": index,
            "test_files_changed": 0,
            "lines_added": index * 10,
            "lines_deleted": index,
            "churn_total": index * 11,
            "is_merge_commit": 0,
            "commit_hour": 10,
            "commit_day_of_week": 2,
            "keyword_risk_score": 0,
            "commit_meta_missing": 0,
        }

    def extract_author_features(self, commit_sha: str, history_df: pd.DataFrame) -> dict:
        current = history_df[history_df["commit_sha"] == commit_sha].iloc[0]
        fallback = int(pd.isna(current["timestamp"]))
        return {
            "author_commit_count_90d": 3,
            "author_failure_rate_90d": 1 / 3,
            "author_feature_fallback": fallback,
            "feature_source": "job_sequence" if fallback else "timestamp",
        }


class FakeTestHistoryExtractor:
    def __init__(self, null_feature: bool = False) -> None:
        self.null_feature = null_feature

    def extract(self, test_id: str, as_of_ts: int, history_df: pd.DataFrame) -> dict:
        return {
            "last_outcome": 0,
            "failure_rate_7d": None if self.null_feature else 0.0,
            "failure_rate_30d": 0.1,
            "failure_rate_90d": 0.2,
            "days_since_last_fail": 5.0,
            "days_since_last_run": 1.0,
            "consecutive_passes": 2,
            "avg_duration_ms": 12.0,
            "duration_variance": 1.5,
            "run_count_30d": 4,
        }


class FakeDependencyExtractor:
    def extract(self, test_id: str, changed_java_files: list[str], repo_path: Path) -> dict:
        return {
            "test_file_touched": int(any(path.endswith("FooTest.java") for path in changed_java_files)),
            "import_overlap": len(changed_java_files),
            "same_package": 0,
            "changed_files_in_module": len(changed_java_files),
            "dependency_parse_failed": 0,
        }


def make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "joiner.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE test_runs (
            repo VARCHAR,
            job_id VARCHAR,
            commit_sha VARCHAR,
            test_id VARCHAR,
            outcome VARCHAR,
            timestamp INTEGER,
            job_sequence INTEGER,
            duration_ms FLOAT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE file_changes (
            repo VARCHAR,
            commit_sha VARCHAR,
            file_path VARCHAR
        )
        """
    )
    runs = []
    for commit_index in range(1, 4):
        for test_name in ("com.example.FooTest", "com.example.BarTest"):
            runs.append(
                (
                    "owner@repo",
                    f"job-{commit_index}-{test_name[-5]}",
                    f"sha{commit_index}",
                    test_name,
                    "FAIL" if commit_index == 2 and "Foo" in test_name else "PASS",
                    commit_index * 1000,
                    commit_index,
                    10.0,
                )
            )
    con.executemany("INSERT INTO test_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", runs)
    con.executemany(
        "INSERT INTO file_changes VALUES (?, ?, ?)",
        [
            ("owner@repo", "sha1", "src/main/java/A.java"),
            ("owner@repo", "sha2", "src/test/java/com/example/FooTest.java"),
            ("owner@repo", "sha3", "src/main/java/C.java"),
        ],
    )
    con.close()
    return db_path


def make_joiner(tmp_path: Path, test_history_extractor=None) -> tuple[FeatureJoiner, FakeCommitExtractor]:
    commit_extractor = FakeCommitExtractor()
    joiner = FeatureJoiner(
        git_root=tmp_path / "git",
        output_dir=tmp_path / "features",
        commit_extractor=commit_extractor,
        test_history_extractor=test_history_extractor or FakeTestHistoryExtractor(),
        dependency_extractor=FakeDependencyExtractor(),
    )
    return joiner, commit_extractor


def test_build_outputs_expected_shape_and_feature_count(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    joiner, _ = make_joiner(tmp_path)

    df = joiner.build("owner@repo", db_path)

    feature_cols = [c for c in df.columns if c not in {"commit_sha", "test_id", "label", "timestamp", "feature_source"}]
    assert df.shape[0] == 6
    assert len(feature_cols) >= 20
    assert (tmp_path / "features" / "owner@repo_features.parquet").exists()


def test_build_includes_expected_columns(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    joiner, _ = make_joiner(tmp_path)

    df = joiner.build("owner@repo", db_path)

    expected = {
        "repo",
        "commit_sha",
        "test_id",
        "label",
        "timestamp",
        "feature_source",
        "files_changed_total",
        "churn_total",
        "author_failure_rate_90d",
        "failure_rate_30d",
        "dependency_parse_failed",
    }
    assert expected.issubset(df.columns)
    assert set(df["label"]) == {0, 1}


def test_commit_level_features_are_cached_and_broadcast_per_commit(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    joiner, commit_extractor = make_joiner(tmp_path)

    df = joiner.build("owner@repo", db_path)

    assert commit_extractor.extract_calls == ["sha1", "sha2", "sha3"]
    for _, group in df.groupby("commit_sha"):
        assert group["churn_total"].nunique() == 1
        assert group["files_changed_total"].nunique() == 1


def test_non_sentinel_null_raises_value_error(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    joiner, _ = make_joiner(tmp_path, FakeTestHistoryExtractor(null_feature=True))

    with pytest.raises(ValueError, match="Unexpected NULL feature values"):
        joiner.build("owner@repo", db_path)
