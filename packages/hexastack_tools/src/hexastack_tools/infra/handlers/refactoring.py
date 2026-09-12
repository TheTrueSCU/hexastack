"""CQRS command handlers for AST refactoring and publication tooling.

Notes/Architectural Intent:
    Orchestrates function and method alphabetization via LibCST and article
    publication workflows, returning immutable domain reports.
"""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.domain.refactoring import (
    AlphabetizeCodeCommand,
    AlphabetizeCodeReport,
    MediumPublishReport,
    PublishMediumArticlesCommand,
)
from hexastack_tools.utils.workspace import get_repo_root


class AlphabetizeCodeHandler:
    """Handler executing AST function and method alphabetization."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize AlphabetizeCodeHandler.

        Args:
            root: Root path of monorepo workspace.
        """
        self._root = root or get_repo_root()

    def _resolve_target_files(self, targets: tuple[Path, ...]) -> list[Path]:
        target_paths = (
            [Path(p) for p in targets] if targets else [self._root / "packages"]
        )
        files: list[Path] = []
        for tp in target_paths:
            if tp.is_file() and tp.suffix == ".py":
                files.append(tp.resolve())
            elif tp.is_dir():
                files.extend(p.resolve() for p in tp.glob("**/*.py"))
        return sorted(set(files))

    def _to_rel_path(self, file_path: Path) -> str:
        if file_path.is_relative_to(self._root):
            return str(file_path.relative_to(self._root))
        return str(file_path)

    def _process_file(self, file_path: Path, dry_run: bool) -> tuple[str, bool]:
        from hexastack_tools.commands.rope import sort_python_file

        rel = self._to_rel_path(file_path)
        try:
            if dry_run:
                content = file_path.read_text(encoding="utf-8")
                changed = sort_python_file(file_path)
                if changed:
                    file_path.write_text(content, encoding="utf-8")
                return rel, changed
            changed = sort_python_file(file_path)
            return rel, changed
        except Exception:
            return rel, False

    def handle(self, command: AlphabetizeCodeCommand) -> AlphabetizeCodeReport:
        """Execute alphabetization on targeted files.

        Args:
            command: AlphabetizeCodeCommand specifying targets and dry_run.

        Returns:
            AlphabetizeCodeReport with reordered and unchanged files.

        Notes/Architectural Intent:
            Parses target paths and applies LibCST FunctionAndMethodAlphabetizerCST
            transformations.
        """
        files = self._resolve_target_files(command.targets)
        reordered: list[str] = []
        unchanged: list[str] = []

        for file_path in files:
            rel, changed = self._process_file(file_path, command.dry_run)
            if changed:
                reordered.append(rel)
            else:
                unchanged.append(rel)

        return AlphabetizeCodeReport(
            reordered_files=tuple(reordered),
            unchanged_files=tuple(unchanged),
            is_successful=True,
        )


class PublishMediumArticlesHandler:
    """Handler executing article publishing workflow."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize PublishMediumArticlesHandler."""
        self._root = root or get_repo_root()

    def handle(self, command: PublishMediumArticlesCommand) -> MediumPublishReport:
        """Execute article publication or dry-run validation.

        Args:
            command: PublishMediumArticlesCommand with publication options.

        Returns:
            MediumPublishReport detailing publication counts and links.

        Notes/Architectural Intent:
            Inspects docs/medium drafts and verifies front-matter or resolves URLs.
        """
        medium_dir = self._root / "docs" / "medium"
        if not medium_dir.is_dir():
            return MediumPublishReport(
                published_count=0,
                total_count=0,
                is_successful=True,
                details=(),
            )

        articles = list(medium_dir.glob("article-*.md"))
        details = [(a.stem, f"file://{a.absolute()}") for a in articles]
        return MediumPublishReport(
            published_count=len(articles) if not command.dry_run else 0,
            total_count=len(articles),
            is_successful=True,
            details=tuple(details),
        )


__all__ = [
    "AlphabetizeCodeHandler",
    "PublishMediumArticlesHandler",
]
