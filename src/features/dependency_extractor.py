"""Dependency/coupling features for changed files and test classes."""

from __future__ import annotations

from pathlib import Path

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
        self._test_context_cache: dict[tuple[str, str], tuple[str, set[str], str, str] | None] = {}
        self._module_cache: dict[tuple[str, str], str] = {}

    def extract(
        self, test_id: str, changed_java_files: list[str], repo_path: str | Path
    ) -> dict[str, int]:
        repo_root = Path(repo_path)
        test_rel = self._test_id_to_path(test_id)
        normalized_changed = [self._normalize_path(path) for path in changed_java_files]
        context = self._load_test_context(repo_root, test_id, test_rel)
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

    @classmethod
    def _find_test_file(cls, repo_root: Path, test_rel: Path) -> Path:
        direct = repo_root / test_rel
        if direct.exists():
            return direct
        matches = list(repo_root.glob(f"**/{cls._normalize_path(test_rel)}"))
        return matches[0] if matches else direct

    def _load_test_context(
        self, repo_root: Path, test_id: str, test_rel: Path
    ) -> tuple[str, set[str], str, str] | None:
        key = (str(repo_root), test_id)
        if key in self._test_context_cache:
            return self._test_context_cache[key]

        test_path = self._find_test_file(repo_root, test_rel)
        if not test_path.exists():
            self._test_context_cache[key] = None
            return None

        try:
            source = test_path.read_text(encoding="utf-8")
            tree = javalang.parse.parse(source)
        except Exception:
            self._test_context_cache[key] = None
            return None

        import_names = {str(import_decl.path) for import_decl in getattr(tree, "imports", [])}
        package_name = getattr(getattr(tree, "package", None), "name", "") or ""
        try:
            test_rel_normalized = self._normalize_path(test_path.relative_to(repo_root))
        except ValueError:
            test_rel_normalized = self._normalize_path(test_rel)
        test_module = self._module_root(test_path, repo_root)
        context = (test_rel_normalized, import_names, package_name, test_module)
        self._test_context_cache[key] = context
        return context

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
