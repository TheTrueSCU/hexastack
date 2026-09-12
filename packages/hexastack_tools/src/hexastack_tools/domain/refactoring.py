"""Domain models and CQRS commands for AST refactoring and publication tooling.

Notes/Architectural Intent:
    Encapsulates command requests and output reports for LibCST/Rope code
    alphabetization and Medium/DEV.to article syndication without external
    HTTP or file modification side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hexastack_core.domain.command import Command


@dataclass(frozen=True)
class AlphabetizeCodeReport:
    """Summary report of LibCST function and method alphabetization.

    Attributes:
        reordered_files: List of file paths modified or reordered.
        unchanged_files: List of file paths already sorted.
        is_successful: True if formatting completed without syntax or AST errors.

    Notes/Architectural Intent:
        Represents alphabetization results for terminal or automated reporting.
    """

    reordered_files: tuple[str, ...] = ()
    unchanged_files: tuple[str, ...] = ()
    is_successful: bool = True


class AlphabetizeCodeCommand(Command):
    """CQRS Command to sort functions and methods alphabetically using LibCST.

    Attributes:
        targets: Specific file or directory paths to audit/format.
        dry_run: Check sorting without modifying files if True.

    Notes/Architectural Intent:
        Encapsulates AST symbol alphabetization parameters.
    """

    targets: tuple[Path, ...] = ()
    dry_run: bool = False


@dataclass(frozen=True)
class MediumPublishReport:
    """Summary report of Medium / DEV.to article publishing.

    Attributes:
        published_count: Number of articles successfully published or updated.
        total_count: Total articles processed.
        is_successful: True if publication or dry-run validation succeeded.
        details: Tuple of (article_slug, target_url_or_id) records.

    Notes/Architectural Intent:
        Aggregates multi-pass article publication status.
    """

    published_count: int = 0
    total_count: int = 0
    is_successful: bool = True
    details: tuple[tuple[str, str], ...] = ()


class PublishMediumArticlesCommand(Command):
    """CQRS Command to execute DEV.to / Medium syndication workflow.

    Attributes:
        manifest_path: Path to articles manifest or directory.
        dry_run: Perform validation without making live HTTP requests.
        publish: Commit publish action if True (otherwise creates drafts).

    Notes/Architectural Intent:
        Decouples publication CLI invocation from API networking.
    """

    manifest_path: Path | None = None
    dry_run: bool = True
    publish: bool = False


__all__ = [
    "AlphabetizeCodeCommand",
    "AlphabetizeCodeReport",
    "MediumPublishReport",
    "PublishMediumArticlesCommand",
]
