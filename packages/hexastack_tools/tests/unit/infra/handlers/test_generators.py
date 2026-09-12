"""Unit tests for generator CQRS command handlers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hexastack_tools.domain.generators import (
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
)
from hexastack_tools.infra.handlers.generators import (
    GenerateArchonTestsHandler,
    GeneratePydepsHandler,
    GenerateUsageDocsHandler,
)


def test_generate_pydeps_handler(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler executes pydeps generation and returns report."""
    handler = GeneratePydepsHandler(root=tmp_path, parallel=False)
    with (
        patch(
            "hexastack_tools.infra.handlers.generators.generate_overview_diagram",
            return_value="docs/overview.svg",
        ),
        patch(
            "hexastack_tools.infra.handlers.generators.generate_package_diagram",
            return_value="docs/core.svg",
        ),
        patch(
            "hexastack_tools.infra.handlers.generators.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
    ):
        report = handler.handle(GeneratePydepsCommand())
        assert report.is_successful is True
        assert len(report.results) >= 1


def test_generate_usage_docs_handler_check_and_fix(tmp_path: Path) -> None:
    """Verify GenerateUsageDocsHandler checks and fixes USAGE.md."""
    usage_file = tmp_path / "USAGE.md"
    usage_file.write_text("Old content\n", encoding="utf-8")

    handler = GenerateUsageDocsHandler(root=tmp_path)
    with (
        patch(
            "hexastack_tools.commands.usage_docs._TARGET_GENERATORS",
            {"test": ("USAGE.md", lambda r: "New content\n")},
        ),
        patch(
            "hexastack_tools.commands.usage_docs.resolve_impacted_usage_targets",
            return_value=["test"],
        ),
    ):
        # Check only -> should report stale
        rep_check = handler.handle(GenerateUsageDocsCommand(check_only=True, fix=False))
        assert rep_check.is_valid is False
        assert len(rep_check.stale_files) == 1

        # Fix mode -> should update file
        rep_fix = handler.handle(GenerateUsageDocsCommand(check_only=False, fix=True))
        assert rep_fix.is_valid is True
        assert usage_file.read_text(encoding="utf-8") == "New content\n"


def test_generate_archon_tests_handler(tmp_path: Path) -> None:
    """Verify GenerateArchonTestsHandler scaffolds architecture test files."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    handler = GenerateArchonTestsHandler(root=tmp_path)

    with (
        patch(
            "hexastack_tools.infra.handlers.generators.get_package_directories",
            return_value=[pkg_dir],
        ),
        patch(
            "hexastack_tools.infra.handlers.generators.get_present_layers",
            return_value=["domain", "ports"],
        ),
    ):
        report = handler.handle(GenerateArchonTestsCommand())
        assert report.is_successful is True
        assert len(report.generated_files) == 1
        test_file = pkg_dir / "tests" / "architecture" / "test_hexagonal_boundaries.py"
        assert test_file.is_file()

        # Running again without force should skip
        rep_skip = handler.handle(GenerateArchonTestsCommand(force=False))
        assert len(rep_skip.skipped_files) == 1
