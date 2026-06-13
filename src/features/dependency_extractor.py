"""Dependency/coupling features for changed files and test classes."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Iterable

import javalang


class DependencyFeatureExtractor:
    """Extract import and module overlap features for a test file."""

    ZERO_FEATURES = {
        "test_file_touched": 0,
        "import_overlap": 0,
        "same_package": 0,
        "changed_files_in_module": 0,
        "dependency_parse_failed": 1,
    }

    def __init__(self) -> None:
        self._test_context_cache: dict[tuple[str, str, str], tuple[str, set[str], str, str] | None] = {}
        self._worktree_attempted: set[tuple[str, str]] = set()
        self._commit_tree_cache: dict[tuple[str, str], tuple[str, ...] | None] = {}
        self._observed_test_paths_by_id: dict[str, list[str]] = {}
        self._observed_test_source_prefixes: set[str] = {"src/test/java/"}
        self._worktree_path_cache: dict[tuple[str, str], Path | None] = {}
        self._module_cache: dict[tuple[str, str], str] = {}

    def add_observed_test_source_paths(self, paths: Iterable[str]) -> None:
        """Prime lookup with test-source paths observed in RTPTorrent patches."""
        for raw_path in paths:
            normalized = self._normalize_path(raw_path)
            if not normalized.lower().endswith(".java"):
                continue
            marker = "src/test/java/"
            if marker not in normalized:
                continue

            prefix, suffix = normalized.split(marker, 1)
            test_id = suffix[:-5].replace("/", ".")
            full_prefix = f"{prefix}{marker}"
            self._observed_test_source_prefixes.add(full_prefix)
            known_paths = self._observed_test_paths_by_id.setdefault(test_id, [])
            if normalized not in known_paths:
                known_paths.append(normalized)

    def extract(
        self,
        test_id: str,
        changed_java_files: list[str],
        repo_path: str | Path,
        commit_sha: str | None = None,
    ) -> dict[str, int]:
        repo_root = Path(repo_path)
        test_rel = self._test_id_to_path(test_id)
        normalized_changed = [self._normalize_path(path) for path in changed_java_files]
        context = self._load_test_context(repo_root, test_id, test_rel, commit_sha)
        if context is None:
            return dict(self.ZERO_FEATURES)

        test_rel_normalized, import_names, package_name, test_module = context

        test_file_touched = int(test_rel_normalized in normalized_changed)
        import_overlap = self._count_import_overlap(import_names, normalized_changed)
        same_package = int(
            any(self._path_to_package(path) == package_name for path in normalized_changed)
        )

        changed_files_in_module = 0
        for changed in normalized_changed:
            changed_path = repo_root / changed
            if self._module_root(changed_path, repo_root) == test_module:
                changed_files_in_module += 1

        return {
            "test_file_touched": test_file_touched,
            "import_overlap": int(import_overlap),
            "same_package": same_package,
            "changed_files_in_module": int(changed_files_in_module),
            "dependency_parse_failed": 0,
        }

    @staticmethod
    def _test_id_to_path(test_id: str) -> Path:
        return Path("src/test/java").joinpath(*test_id.split(".")).with_suffix(".java")

    def _find_test_file(self, repo_root: Path, test_rel: Path, test_id: str | None = None) -> Path:
        cache_key = (str(repo_root), str(test_id or self._normalize_path(test_rel)))
        if cache_key in self._worktree_path_cache:
            cached = self._worktree_path_cache[cache_key]
            return cached if cached is not None else repo_root / test_rel

        direct = repo_root / test_rel
        if direct.exists():
            self._worktree_path_cache[cache_key] = direct
            return direct

        for candidate in self._candidate_test_paths(str(test_id or ""), test_rel):
            path = repo_root / candidate
            if path.exists():
                self._worktree_path_cache[cache_key] = path
                return path

        matches = list(repo_root.glob(f"**/{self._normalize_path(test_rel)}"))
        if matches:
            self._worktree_path_cache[cache_key] = matches[0]
            return matches[0]
        self._worktree_path_cache[cache_key] = None
        return direct

    def _load_test_context(
        self,
        repo_root: Path,
        test_id: str,
        test_rel: Path,
        commit_sha: str | None = None,
    ) -> tuple[str, set[str], str, str] | None:
        repo_key = str(repo_root)
        worktree_key = (repo_key, test_id)
        cache_key = (repo_key, test_id, str(commit_sha or ""))
        if cache_key in self._test_context_cache:
            return self._test_context_cache[cache_key]

        worktree_cache_key = (repo_key, test_id, "worktree")
        if worktree_cache_key in self._test_context_cache:
            return self._test_context_cache[worktree_cache_key]

        if worktree_key not in self._worktree_attempted:
            self._worktree_attempted.add(worktree_key)
            context = self._load_worktree_context(repo_root, test_id, test_rel)
            if context is not None:
                self._test_context_cache[worktree_cache_key] = context
                return context

        if commit_sha:
            context = self._load_historical_context(repo_root, test_id, test_rel, str(commit_sha))
            self._test_context_cache[cache_key] = context
            return context

        self._test_context_cache[cache_key] = None
        return None

    def _load_worktree_context(
        self, repo_root: Path, test_id: str, test_rel: Path
    ) -> tuple[str, set[str], str, str] | None:
        test_path = self._find_test_file(repo_root, test_rel, test_id)
        if not test_path.exists():
            return None

        try:
            source = test_path.read_text(encoding="utf-8")
        except Exception:
            return None

        try:
            test_rel_normalized = self._normalize_path(test_path.relative_to(repo_root))
        except ValueError:
            test_rel_normalized = self._normalize_path(test_rel)
        return self._parse_source_context(source, repo_root, test_rel_normalized)

    def _load_historical_context(
        self, repo_root: Path, test_id: str, test_rel: Path, commit_sha: str
    ) -> tuple[str, set[str], str, str] | None:
        candidates = self._candidate_test_paths(test_id, test_rel)
        for historical_path in candidates:
            source = self._read_historical_source(repo_root, commit_sha, historical_path)
            if source is None:
                continue
            context = self._parse_source_context(source, repo_root, historical_path)
            if context is not None:
                return context

        if self._observed_test_paths_by_id.get(test_id) or len(candidates) > 1:
            return None
        return self._load_historical_context_from_tree(repo_root, test_id, test_rel, commit_sha)

    def _parse_source_context(
        self, source: str, repo_root: Path, test_rel_normalized: str
    ) -> tuple[str, set[str], str, str] | None:
        try:
            tree = javalang.parse.parse(source)
        except Exception:
            return None

        import_names = {str(import_decl.path) for import_decl in getattr(tree, "imports", [])}
        package_name = getattr(getattr(tree, "package", None), "name", "") or ""
        test_module = self._module_root(repo_root / test_rel_normalized, repo_root)
        return (test_rel_normalized, import_names, package_name, test_module)

    def _load_historical_context_from_tree(
        self, repo_root: Path, commit_sha: str, test_id: str, test_rel: Path
    ) -> tuple[str, set[str], str, str] | None:
        paths = self._commit_tree_paths(repo_root, commit_sha)
        if paths is None:
            return None

        normalized_test_rel = self._normalize_path(test_rel)
        suffix = f"/{normalized_test_rel}"
        exact_matches = [
            path for path in paths if path == normalized_test_rel or path.endswith(suffix)
        ]
        if exact_matches:
            for path in sorted(exact_matches, key=len):
                source = self._read_historical_source(repo_root, commit_sha, path)
                if source is None:
                    continue
                context = self._parse_source_context(source, repo_root, path)
                if context is not None:
                    return context

        class_file = f"{test_id.split('.')[-1]}.java"
        filename_matches = [
            path
            for path in paths
            if path.endswith(f"/{class_file}") and "/src/test/java/" in f"/{path}"
        ]
        for path in sorted(filename_matches, key=len):
            source = self._read_historical_source(repo_root, commit_sha, path)
            if source is None:
                continue
            context = self._parse_source_context(source, repo_root, path)
            if context is not None:
                return context
        return None

    def _candidate_test_paths(self, test_id: str, test_rel: Path) -> list[str]:
        normalized_test_rel = self._normalize_path(test_rel)
        suffix = normalized_test_rel.split("src/test/java/", 1)[-1]
        candidates: list[str] = [normalized_test_rel]

        observed_paths = self._observed_test_paths_by_id.get(test_id, [])
        for path in observed_paths:
            if path not in candidates:
                candidates.append(path)
        if observed_paths:
            return candidates

        for prefix in sorted(self._observed_test_source_prefixes, key=len):
            path = f"{prefix}{suffix}"
            if path not in candidates:
                candidates.append(path)
        return candidates

    def _commit_tree_paths(self, repo_root: Path, commit_sha: str) -> tuple[str, ...] | None:
        key = (str(repo_root), commit_sha)
        if key in self._commit_tree_cache:
            return self._commit_tree_cache[key]

        result = self._run_git(repo_root, "ls-tree", "-r", "--name-only", commit_sha)
        if result.returncode != 0:
            self._commit_tree_cache[key] = None
            return None

        paths = tuple(
            self._normalize_path(line.strip())
            for line in result.stdout.splitlines()
            if line.strip()
        )
        self._commit_tree_cache[key] = paths
        return paths

    def _read_historical_source(
        self, repo_root: Path, commit_sha: str, test_path: str
    ) -> str | None:
        result = self._run_git(repo_root, "show", f"{commit_sha}:{test_path}")
        if result.returncode != 0:
            return None
        return result.stdout

    @staticmethod
    def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["GIT_NO_LAZY_FETCH"] = "1"
        return subprocess.run(
            ["git", "-c", f"safe.directory={repo_root.resolve().as_posix()}", *args],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    @staticmethod
    def _normalize_path(path: str | Path) -> str:
        return str(path).replace("\\", "/").lstrip("./")

    @staticmethod
    def _count_import_overlap(import_names: set[str], changed_paths: list[str]) -> int:
        count = 0
        for path in changed_paths:
            if not path.lower().endswith(".java"):
                continue
            class_name = Path(path).stem
            if any(import_name == class_name or import_name.endswith(f".{class_name}") for import_name in import_names):
                count += 1
        return count

    @classmethod
    def _path_to_package(cls, path: str) -> str:
        normalized = cls._normalize_path(path)
        for marker in ("src/main/java/", "src/test/java/"):
            if marker in normalized:
                package_path = normalized.split(marker, 1)[1]
                parts = package_path.split("/")[:-1]
                return ".".join(parts)
        return ""

    def _module_root(self, path: Path, repo_root: Path) -> str:
        key = (str(repo_root), self._normalize_path(path))
        if key in self._module_cache:
            return self._module_cache[key]
        value = self._module_root_uncached(path, repo_root)
        self._module_cache[key] = value
        return value

    @classmethod
    def _module_root_uncached(cls, path: Path, repo_root: Path) -> str:
        path = path if path.is_dir() else path.parent
        try:
            path.relative_to(repo_root)
        except ValueError:
            return ""

        current = path
        while True:
            if (current / "pom.xml").exists():
                return cls._normalize_path(current.relative_to(repo_root))
            if current == repo_root:
                break
            current = current.parent

        try:
            relative = path.relative_to(repo_root)
        except ValueError:
            return ""
        return relative.parts[0] if relative.parts else "."
