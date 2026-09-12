"""Domain models and CQRS commands for code and documentation generators.

Notes/Architectural Intent:
    Encapsulates command requests and output reports for pydeps dependency
    diagrams, USAGE.md catalog synchronization, and pytest-archon hexagonal
    boundary test scaffolding without subprocess or presentation dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexastack_core.domain.command import Command


@dataclass(frozen=True)
class PydepsDiagramResult:
    """Represents a generated pydeps dependency diagram result.

    Attributes:
        name: Name of the package or overview diagram.
        path: Path where the SVG diagram was written.
        success: Whether the diagram generation succeeded.

    Notes/Architectural Intent:
        Encapsulates individual diagram output metadata for multi-format
        presentation and CI verification.
    """

    name: str
    path: str
    success: bool = True


@dataclass(frozen=True)
class PydepsReport:
    """Summary report of pydeps architecture diagram generation.

    Attributes:
        results: Tuple of generated diagram results.
        is_successful: True if all requested diagrams generated successfully.

    Notes/Architectural Intent:
        Represents the immutable aggregate output of pydeps diagram generation
        suitable for rich console tables or machine-readable JSON.
    """

    results: tuple[PydepsDiagramResult, ...] = ()
    is_successful: bool = True


class GeneratePydepsCommand(Command):
    """CQRS Command to generate architecture dependency diagrams via pydeps.

    Attributes:
        packages: Optional tuple of specific package names to generate diagrams for.

    Notes/Architectural Intent:
        Dispatches diagram generation through the governance bus, decoupling
        the CLI entrypoint from concurrent multiprocessing workers.
    """

    packages: tuple[str, ...] = ()


@dataclass(frozen=True)
class UsageDocsReport:
    """Summary report of USAGE.md documentation checks or updates.

    Attributes:
        up_to_date_files: Paths to USAGE.md files that are current.
        updated_files: Paths to USAGE.md files that were updated.
        stale_files: Paths to USAGE.md files that are out of date.
        diffs: Tuple of (file_path, diff_content) pairs for stale files.
        is_valid: True if all files are up-to-date (or were successfully fixed).

    Notes/Architectural Intent:
        Supports both read-only validation (pre-commit quality gate) and
        mutation fix mode, reporting unified status across workspace packages.
    """

    up_to_date_files: tuple[str, ...] = ()
    updated_files: tuple[str, ...] = ()
    stale_files: tuple[str, ...] = ()
    diffs: tuple[tuple[str, str], ...] = ()
    is_valid: bool = True


class GenerateUsageDocsCommand(Command):
    """CQRS Command to audit or generate USAGE.md files across the workspace.

    Attributes:
        check_only: Only verify documentation freshness without modifying files.
        fix: Automatically update stale USAGE.md files.
        affected_only: Restrict check/generation to packages affected by git diff.

    Notes/Architectural Intent:
        Decouples CLI argument parsing from parallel help-tree extraction
        and file diffing logic.
    """

    package: str | None = None
    check_only: bool = False
    fix: bool = False
    affected_only: bool = False


@dataclass(frozen=True)
class ArchonReport:
    """Summary report of pytest-archon boundary test scaffolding.

    Attributes:
        generated_files: Paths to created test files.
        skipped_files: Paths to packages skipped because layers were absent.
        is_successful: True if all eligible packages were scaffolded without error.

    Notes/Architectural Intent:
        Captures files created or skipped during archon test scaffolding.
    """

    generated_files: tuple[str, ...] = ()
    skipped_files: tuple[str, ...] = ()
    is_successful: bool = True


class GenerateArchonTestsCommand(Command):
    """CQRS Command to scaffold or regenerate pytest-archon boundary tests.

    Attributes:
        packages: Optional tuple of specific package names to generate tests for.
        force: Overwrite existing test files if True.

    Notes/Architectural Intent:
        Encapsulates pytest-archon boundary test generation parameters.
    """

    packages: tuple[str, ...] = ()
    force: bool = False


__all__ = [
    "ArchonReport",
    "GenerateArchonTestsCommand",
    "GeneratePydepsCommand",
    "GenerateUsageDocsCommand",
    "PydepsDiagramResult",
    "PydepsReport",
    "UsageDocsReport",
]
