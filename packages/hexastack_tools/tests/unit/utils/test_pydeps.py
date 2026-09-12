"""Unit tests for pydeps diagram generation utilities.

Notes/Architectural Intent:
    Tests SVG output directory creation, package diagram generation with mocks,
    and overview diagram generation without requiring external graphviz/pydeps binaries.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hexastack_tools.utils.pydeps import (
    _output_dir,
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)


def test_output_dir(tmp_path: Path) -> None:
    """Verify _output_dir creates directory if missing."""
    out = _output_dir(tmp_path)
    assert out.is_dir()
    assert out == tmp_path / "docs" / "assets" / "pydeps"


def test_generate_package_diagram_no_entry_point(tmp_path: Path) -> None:
    """Verify None returned when package has no src/<name> dir."""
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    res = generate_package_diagram(pkg, tmp_path)
    assert res is None


def test_generate_package_diagram_success(tmp_path: Path) -> None:
    """Verify SVG path returned when pydeps completes."""
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)

    with patch("hexastack_tools.utils.pydeps.pydeps") as mock_pydeps:
        res = generate_package_diagram(pkg, tmp_path)
        assert res is not None
        assert "my_pkg.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_overview_diagram(tmp_path: Path) -> None:
    """Verify overview diagram generation."""
    with patch("hexastack_tools.utils.pydeps.pydeps") as mock_pydeps:
        res = generate_overview_diagram(tmp_path)
        assert res is not None
        assert "hexastack_packages.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_all_diagrams(tmp_path: Path) -> None:
    """Verify generate_all_diagrams invokes overview and packages."""
    with (
        patch("hexastack_tools.utils.pydeps.ensure_tool_installed"),
        patch(
            "hexastack_tools.utils.pydeps.get_package_directories",
            return_value=[],
        ),
        patch(
            "hexastack_tools.utils.pydeps.generate_overview_diagram",
            return_value="docs/assets/pydeps/hexastack_packages.svg",
        ),
    ):
        results = generate_all_diagrams(tmp_path)
        assert len(results) == 1
        assert results[0][0] == "Monorepo Overview"
