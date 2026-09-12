"""Unit tests for PyPiClientPort and PyPiPresenterPort."""

from __future__ import annotations

from pathlib import Path

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
from hexastack_tools.ports.pypi import PyPiClientPort, PyPiPresenterPort


class DummyPyPiClient:
    """Dummy implementation of PyPiClientPort for protocol verification."""

    def check_version_exists(self, package_name: str, version: str) -> bool:
        return True

    def build_package(
        self, package_name: str, out_dir: Path, env: dict[str, str] | None = None
    ) -> tuple[bool, str]:
        return True, "built"

    def publish_package(
        self, files: list[Path], token: str | None = None
    ) -> tuple[bool, str]:
        return True, "published"

    def get_git_commit_epoch(self) -> str | None:
        return "1700000000"


class DummyPyPiPresenter(PyPiPresenterPort):
    """Dummy implementation of PyPiPresenterPort for interface verification."""

    def present_check(self, report: PyPiCheckReport) -> int:
        return 0

    def present_build(self, report: PyPiBuildReport) -> int:
        return 0

    def present_publish(self, report: PyPiPublishReport) -> int:
        return 0

    def present_reproducible(self, report: ReproducibleBuildReport) -> int:
        return 0


def test_pypi_client_port_protocol() -> None:
    """Verify DummyPyPiClient satisfies PyPiClientPort protocol."""
    client = DummyPyPiClient()
    assert isinstance(client, PyPiClientPort)
    assert client.check_version_exists("pkg", "1.0") is True
    assert client.build_package("pkg", Path("/tmp")) == (True, "built")
    assert client.publish_package([Path("/tmp/pkg.whl")]) == (True, "published")
    assert client.get_git_commit_epoch() == "1700000000"


def test_pypi_presenter_port_abstract_methods() -> None:
    """Verify DummyPyPiPresenter implements all required methods."""
    presenter = DummyPyPiPresenter()
    meta = PackageMetadata(
        name="pkg",
        version="1.0",
        dir_path=Path("/pkg"),
        pyproject_path=Path("/pkg/pyproject.toml"),
    )

    check_rep = PyPiCheckReport(
        checks=(PackageReleaseCheck(package=meta, exists=True),)
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
                package_name="pkg",
                artifact_name="pkg.whl",
                hash1="a",
                hash2="a",
                is_reproducible=True,
            ),
        ),
    )

    assert presenter.present_check(check_rep) == 0
    assert presenter.present_build(build_rep) == 0
    assert presenter.present_publish(pub_rep) == 0
    assert presenter.present_reproducible(repro_rep) == 0
