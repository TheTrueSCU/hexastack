"""Unit tests for usage_docs generator command."""

from hexastack_tools.commands.usage_docs import (
    build_tools_usage_markdown,
    build_umbrella_usage_markdown,
    main,
    resolve_impacted_usage_targets,
)
from hexastack_tools.utils.workspace import get_repo_root


def test_build_tools_usage_markdown_contains_sections() -> None:
    """Ensure generated tools markdown contains expected sections and headers."""
    root = get_repo_root()
    content = build_tools_usage_markdown(root)
    assert "# Hexastack Developer Tools & Usage Guide" in content
    assert "gh-pr-examine" in content
    assert "check-test-parity" in content
    assert "pytest-run" in content


def test_build_umbrella_usage_markdown_contains_sections() -> None:
    """Ensure generated umbrella hexastack markdown contains expected sections."""
    root = get_repo_root()
    content = build_umbrella_usage_markdown(root)
    assert "# Hexastack CLI & Framework Usage Guide" in content
    assert "Unified Entrypoint (`hexastack`)" in content


def test_resolve_impacted_usage_targets() -> None:
    """Ensure impacted targets returns a valid list of targets."""
    root = get_repo_root()
    targets = resolve_impacted_usage_targets(root)
    assert isinstance(targets, list)
    assert len(targets) > 0


def test_usage_docs_main_callable() -> None:
    """Verify CLI entrypoint is callable."""
    assert callable(main)
