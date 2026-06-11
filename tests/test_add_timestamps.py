from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from scripts import add_timestamps


BadName = type("BadName", (Exception,), {})


class FakeCommit:
    def __init__(self, committed_date: int) -> None:
        self.committed_date = committed_date


class FakeRepo:
    def __init__(self, dates: dict[str, int]) -> None:
        self.dates = dates
        self.calls: list[str] = []

    def commit(self, commit_sha: str) -> FakeCommit:
        self.calls.append(commit_sha)
        if commit_sha not in self.dates:
            raise BadName(commit_sha)
        return FakeCommit(self.dates[commit_sha])


def create_test_db(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(str(tmp_path / "test_history.db"))
    connection.execute(
        """
        CREATE SEQUENCE test_runs_id_seq START 1;
        CREATE TABLE test_runs (
            id BIGINT PRIMARY KEY DEFAULT nextval('test_runs_id_seq'),
            repo TEXT NOT NULL,
            job_id TEXT NOT NULL,
            commit_sha TEXT,
            test_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            timestamp INTEGER,
            job_sequence INTEGER
        );
        """
    )
    return connection


def insert_run(
    connection: duckdb.DuckDBPyConnection,
    repo: str,
    job_id: str,
    commit_sha: str | None,
    test_id: str,
    timestamp: int | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO test_runs (
            repo, job_id, commit_sha, test_id, outcome, timestamp, job_sequence
        )
        VALUES (?, ?, ?, ?, 'PASS', ?, 1);
        """,
        (repo, job_id, commit_sha, test_id, timestamp),
    )
    connection.commit()


def make_git_repo_dir(tmp_path: Path, project: str) -> Path:
    git_root = tmp_path / "git-repos"
    (git_root / project).mkdir(parents=True)
    return git_root


def timestamps_by_test(connection: duckdb.DuckDBPyConnection) -> dict[str, int | None]:
    rows = connection.execute(
        "SELECT test_id, timestamp FROM test_runs ORDER BY test_id;"
    ).fetchall()
    return {test_id: timestamp for test_id, timestamp in rows}


def test_resolves_shas_and_updates_all_matching_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = "owner@repo"
    connection = create_test_db(tmp_path)
    insert_run(connection, project, "1", "sha-a", "test-a")
    insert_run(connection, project, "2", "sha-a", "test-b")
    insert_run(connection, project, "3", "sha-b", "test-c")
    insert_run(connection, project, "4", "sha-c", "test-d")
    insert_run(connection, project, "5", None, "test-null-sha")
    git_root = make_git_repo_dir(tmp_path, project)
    fake_repo = FakeRepo({"sha-a": 100, "sha-b": 200, "sha-c": 300})
    monkeypatch.setattr(add_timestamps, "create_git_repo", lambda path: fake_repo)

    report = add_timestamps.resolve_project_timestamps(
        connection, project, git_root, dry_run=False
    )

    assert report.resolved_shas == 3
    assert report.total_shas == 3
    assert report.timestamped_rows == 4
    assert timestamps_by_test(connection) == {
        "test-a": 100,
        "test-b": 100,
        "test-c": 200,
        "test-d": 300,
        "test-null-sha": None,
    }


def test_missing_sha_is_skipped_and_counted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = "owner@repo"
    connection = create_test_db(tmp_path)
    insert_run(connection, project, "1", "sha-a", "test-a")
    insert_run(connection, project, "2", "sha-missing", "test-b")
    git_root = make_git_repo_dir(tmp_path, project)
    fake_repo = FakeRepo({"sha-a": 100})
    monkeypatch.setattr(add_timestamps, "create_git_repo", lambda path: fake_repo)

    report = add_timestamps.resolve_project_timestamps(
        connection, project, git_root, dry_run=False
    )

    assert report.resolved_shas == 1
    assert report.sha_not_found == 1
    assert timestamps_by_test(connection) == {"test-a": 100, "test-b": None}


def test_already_timestamped_sha_is_skipped_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = "owner@repo"
    connection = create_test_db(tmp_path)
    insert_run(connection, project, "1", "sha-existing", "test-a", timestamp=123)
    insert_run(connection, project, "2", "sha-new", "test-b")
    git_root = make_git_repo_dir(tmp_path, project)
    fake_repo = FakeRepo({"sha-new": 456})
    monkeypatch.setattr(add_timestamps, "create_git_repo", lambda path: fake_repo)

    report = add_timestamps.resolve_project_timestamps(
        connection, project, git_root, dry_run=False
    )

    assert fake_repo.calls == ["sha-new"]
    assert report.resolved_shas == 2
    assert timestamps_by_test(connection) == {"test-a": 123, "test-b": 456}


def test_coverage_gate_fails_below_threshold() -> None:
    report = add_timestamps.ProjectTimestampReport(
        project="owner@repo",
        total_shas=10,
        resolved_shas=6,
        eligible_rows=100,
        timestamped_rows=80,
    )

    assert not report.passes(min_sha_coverage=70, min_row_coverage=70)


def test_dry_run_does_not_update_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = "owner@repo"
    connection = create_test_db(tmp_path)
    insert_run(connection, project, "1", "sha-a", "test-a")
    git_root = make_git_repo_dir(tmp_path, project)
    fake_repo = FakeRepo({"sha-a": 100})
    monkeypatch.setattr(add_timestamps, "create_git_repo", lambda path: fake_repo)

    report = add_timestamps.resolve_project_timestamps(
        connection, project, git_root, dry_run=True
    )

    assert report.resolved_shas == 1
    assert report.timestamped_rows == 1
    assert timestamps_by_test(connection) == {"test-a": None}


def test_missing_repo_counts_all_unresolved_shas(tmp_path: Path) -> None:
    project = "owner@repo"
    connection = create_test_db(tmp_path)
    insert_run(connection, project, "1", "sha-a", "test-a")
    insert_run(connection, project, "2", "sha-b", "test-b")
    git_root = tmp_path / "git-repos"
    git_root.mkdir()

    report = add_timestamps.resolve_project_timestamps(
        connection, project, git_root, dry_run=False
    )

    assert report.missing_repo == 2
    assert report.resolved_shas == 0
    assert timestamps_by_test(connection) == {"test-a": None, "test-b": None}

def test_read_projects_from_summary_only_returns_selected_rows(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "| Project | Builds | Tests | Failure Rate | Status |",
                "|---------|--------|-------|--------------|--------|",
                "| owner@selected | 10 | 20 | 2.0% | SELECTED |",
                "| owner@not-selected | 10 | 20 | 0.2% | NOT SELECTED (failure rate < 1%) |",
            ]
        ),
        encoding="utf-8",
    )

    projects = add_timestamps.read_projects_from_summary(summary_path)

    assert projects == ["owner@selected"]


def test_add_process_safe_directory_sets_git_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    add_timestamps.add_process_safe_directory(repo_path)
    add_timestamps.add_process_safe_directory(repo_path)

    assert add_timestamps.os.environ["GIT_CONFIG_COUNT"] == "1"
    assert add_timestamps.os.environ["GIT_CONFIG_KEY_0"] == "safe.directory"
    assert (
        add_timestamps.os.environ["GIT_CONFIG_VALUE_0"]
        == repo_path.resolve().as_posix()
    )
