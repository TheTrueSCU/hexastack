"""Unit tests for PyPI multi-format presenters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from rich.console import Console

from hexastack_tools.adapters.presenters.pypi import (
    JsonPyPiPresenterAdapter,
    MarkdownPyPiPresenterAdapter,
    RichPyPiPresenterAdapter,
    create_pypi_presenter,
)
from hexastack_tools.domain.pypi import (
    PackageBuildResult,
    PackageMetadata,
    PackagePublishResult,
    PackageReleaseCheck,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleArtifactResult,
    ReproducibleBuildReport,
)


def _sample_reports() -> tuple[
    PyPiCheckReport,
    PyPiBuildReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
]:
    meta = PackageMetadata(
        name="hexastack-core",
        version="0.1.0",
        dir_path=Path("/pkg"),
        pyproject_path=Path("/pkg/pyproject.toml"),
    )
    check_rep = PyPiCheckReport(
        checks=(PackageReleaseCheck(package=meta, exists=False),)
    )
    build_rep = PyPiBuildReport(
        target_dist=Path("/dist"),
        results=(PackageBuildResult(package=meta, success=True),),
    )
    pub_rep = PyPiPublishReport(
        results=(
            PackagePublishResult(package=meta, outcome="published", is_success=True),
        )
    )
    repro_rep = ReproducibleBuildReport(
        epoch="1700000000",
        results=(
            ReproducibleArtifactResult(
                package_name="hexastack-core",
                artifact_name="hexastack_core-0.1.0.whl",
                hash1="abc",
                hash2="abc",
                is_reproducible=True,
            ),
        ),
    )
    return check_rep, build_rep, pub_rep, repro_rep


def test_rich_pypi_presenter() -> None:
    """Test RichPyPiPresenterAdapter methods."""
    mock_console = MagicMock(spec=Console)
    presenter = RichPyPiPresenterAdapter(console=mock_console)

    check_rep, build_rep, pub_rep, repro_rep = _sample_reports()

    assert presenter.present_check(check_rep) == 0
    assert presenter.present_build(build_rep) == 0
    assert presenter.present_publish(pub_rep) == 0
    assert presenter.present_reproducible(repro_rep) == 0
    assert mock_console.print.call_count >= 4


def test_rich_pypi_presenter_failures() -> None:
    """Test RichPyPiPresenterAdapter with failed reports."""
    mock_console = MagicMock(spec=Console)
    presenter = RichPyPiPresenterAdapter(console=mock_console)

    meta = PackageMetadata(
        name="failed-pkg",
        version="0.1.0",
        dir_path=Path("/pkg"),
        pyproject_path=Path("/pkg/pyproject.toml"),
    )
    build_fail = PyPiBuildReport(
        target_dist=Path("/dist"),
        results=(PackageBuildResult(package=meta, success=False),),
    )
    pub_fail = PyPiPublishReport(
        results=(
            PackagePublishResult(
                package=meta, outcome="failed", is_success=False, detail="429"
            ),
            PackagePublishResult(
                package=meta,
                outcome="skipped",
                is_success=False,
                detail="already exists",
            ),
        )
    )
    repro_fail = ReproducibleBuildReport(
        epoch="1700000000",
        results=(
            ReproducibleArtifactResult(
                package_name="failed-pkg",
                artifact_name="pkg.whl",
                hash1="a",
                hash2="b",
                is_reproducible=False,
            ),
        ),
    )

    assert presenter.present_build(build_fail) == 1
    assert presenter.present_publish(pub_fail) == 1
    assert presenter.present_reproducible(repro_fail) == 1


def test_json_pypi_presenter() -> None:
    """Test JsonPyPiPresenterAdapter outputs."""
    mock_console = MagicMock(spec=Console)
    presenter = JsonPyPiPresenterAdapter(console=mock_console)

    check_rep, build_rep, pub_rep, repro_rep = _sample_reports()

    assert presenter.present_check(check_rep) == 0
    assert presenter.present_build(build_rep) == 0
    assert presenter.present_publish(pub_rep) == 0
    assert presenter.present_reproducible(repro_rep) == 0
    assert mock_console.print_json.call_count == 4


def test_markdown_pypi_presenter() -> None:
    """Test MarkdownPyPiPresenterAdapter outputs."""
    mock_console = MagicMock(spec=Console)
    presenter = MarkdownPyPiPresenterAdapter(console=mock_console)

    check_rep, build_rep, pub_rep, repro_rep = _sample_reports()

    assert presenter.present_check(check_rep) == 0
    assert presenter.present_build(build_rep) == 0
    assert presenter.present_publish(pub_rep) == 0
    assert presenter.present_reproducible(repro_rep) == 0
    assert mock_console.print.call_count == 4


def test_create_pypi_presenter_factory() -> None:
    """Test create_pypi_presenter factory."""
    assert isinstance(create_pypi_presenter("json"), JsonPyPiPresenterAdapter)
    assert isinstance(create_pypi_presenter("markdown"), MarkdownPyPiPresenterAdapter)
    assert isinstance(create_pypi_presenter("rich"), RichPyPiPresenterAdapter)
    assert isinstance(create_pypi_presenter(None), RichPyPiPresenterAdapter)
