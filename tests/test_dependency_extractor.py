from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from src.features.dependency_extractor import DependencyFeatureExtractor


JAVA_SOURCE = """
package com.example;

import com.other.Foo;
import com.another.Bar;

public class FooTest { }
"""


def write_test_file(repo: Path, source: str = JAVA_SOURCE) -> Path:
    path = repo / "src" / "test" / "java" / "com" / "example" / "FooTest.java"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_file_not_found_returns_zero_features_with_parse_failed(tmp_path: Path) -> None:
    result = DependencyFeatureExtractor().extract("com.example.FooTest", [], tmp_path)

    assert result == DependencyFeatureExtractor.ZERO_FEATURES


def test_parse_failure_returns_zero_features_with_parse_failed(tmp_path: Path) -> None:
    write_test_file(tmp_path, "package com.example; public class FooTest {")

    result = DependencyFeatureExtractor().extract("com.example.FooTest", [], tmp_path)

    assert result == DependencyFeatureExtractor.ZERO_FEATURES


def test_test_file_touched_when_test_path_in_changed_files(tmp_path: Path) -> None:
    write_test_file(tmp_path)

    result = DependencyFeatureExtractor().extract(
        "com.example.FooTest",
        ["src/test/java/com/example/FooTest.java"],
        tmp_path,
    )

    assert result["test_file_touched"] == 1
    assert result["dependency_parse_failed"] == 0


def test_import_overlap_counts_changed_classes_in_imports(tmp_path: Path) -> None:
    write_test_file(tmp_path)

    result = DependencyFeatureExtractor().extract(
        "com.example.FooTest",
        ["src/main/java/com/other/Foo.java", "src/main/java/com/another/Bar.java"],
        tmp_path,
    )

    assert result["import_overlap"] == 2


def test_same_package_detects_changed_source_package_match(tmp_path: Path) -> None:
    write_test_file(tmp_path)

    result = DependencyFeatureExtractor().extract(
        "com.example.FooTest",
        ["src/main/java/com/example/Service.java"],
        tmp_path,
    )

    assert result["same_package"] == 1


def test_changed_files_in_module_counts_nearest_pom_module(tmp_path: Path) -> None:
    module = tmp_path / "module-a"
    (module / "pom.xml").parent.mkdir(parents=True, exist_ok=True)
    (module / "pom.xml").write_text("<project />", encoding="utf-8")
    test_path = module / "src" / "test" / "java" / "com" / "example" / "FooTest.java"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(JAVA_SOURCE, encoding="utf-8")

    result = DependencyFeatureExtractor().extract(
        "com.example.FooTest",
        [
            "module-a/src/main/java/com/example/Service.java",
            "module-a/src/main/java/com/other/Foo.java",
            "module-b/src/main/java/com/example/Other.java",
        ],
        tmp_path,
    )

    assert result["changed_files_in_module"] == 2


def test_module_fallback_uses_top_level_directory_without_pom(tmp_path: Path) -> None:
    write_test_file(tmp_path)

    result = DependencyFeatureExtractor().extract(
        "com.example.FooTest",
        ["src/main/java/com/example/Service.java", "other/src/main/java/com/example/Other.java"],
        tmp_path,
    )

    assert result["changed_files_in_module"] == 1


def test_historical_commit_source_is_used_when_worktree_file_is_missing(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git CLI is required for historical source lookup")

    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "dev@example.com")
    run_git(repo, "config", "user.name", "Dev")
    write_test_file(repo)
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "add test")
    historical_sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "src" / "test" / "java" / "com" / "example" / "FooTest.java").unlink()
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "delete test")

    subject = DependencyFeatureExtractor()
    subject.add_observed_test_source_paths(["src/test/java/com/example/FooTest.java"])

    result = subject.extract(
        "com.example.FooTest",
        ["src/test/java/com/example/FooTest.java"],
        repo,
        commit_sha=historical_sha,
    )

    assert result["dependency_parse_failed"] == 0
    assert result["test_file_touched"] == 1


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
