"""Unit tests for PyPI domain models and commands."""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PackageBuildResult,
    PackageMetadata,
    PackagePublishResult,
    PackageReleaseCheck,
    PublishPackagesCommand,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleArtifactResult,
    ReproducibleBuildReport,
    VerifyReproducibleBuildCommand,
)


def test_package_metadata_and_release_check() -> None:
    """Test PackageMetadata and PackageReleaseCheck instantiation."""
    meta = PackageMetadata(
        name="hexastack-core",
        version="0.1.0",
        dir_path=Path("/workspace/packages/hexastack_core"),
        pyproject_path=Path("/workspace/packages/hexastack_core/pyproject.toml"),
    )
    check = PackageReleaseCheck(package=meta, exists=True)
    report = PyPiCheckReport(checks=(check,))

    assert len(report.checks) == 1
    assert report.checks[0].exists is True
    assert report.checks[0].package.name == "hexastack-core"


def test_pypi_build_report() -> None:
    """Test PyPiBuildReport properties."""
    meta1 = PackageMetadata(
        name="pkg-a",
        version="1.0.0",
        dir_path=Path("/pkg-a"),
        pyproject_path=Path("/pkg-a/pyproject.toml"),
    )
    meta2 = PackageMetadata(
        name="pkg-b",
        version="1.0.0",
        dir_path=Path("/pkg-b"),
        pyproject_path=Path("/pkg-b/pyproject.toml"),
    )
    res1 = PackageBuildResult(package=meta1, success=True)
    res2 = PackageBuildResult(package=meta2, success=False, output="Error")

    rep_ok = PyPiBuildReport(target_dist=Path("/dist"), results=(res1,))
    assert rep_ok.has_failure is False

    rep_fail = PyPiBuildReport(target_dist=Path("/dist"), results=(res1, res2))
    assert rep_fail.has_failure is True


def test_pypi_publish_report() -> None:
    """Test PyPiPublishReport counts and failure detection."""
    meta = PackageMetadata(
        name="pkg",
        version="1.0.0",
        dir_path=Path("/pkg"),
        pyproject_path=Path("/pkg/pyproject.toml"),
    )
    r1 = PackagePublishResult(package=meta, outcome="published", is_success=True)
    r2 = PackagePublishResult(package=meta, outcome="skipped", is_success=False)
    r3 = PackagePublishResult(
        package=meta, outcome="failed", is_success=False, detail="429"
    )

    report = PyPiPublishReport(results=(r1, r2, r3))
    counts = report.counts
    assert counts["published"] == 1
    assert counts["skipped"] == 1
    assert counts["failed"] == 1
    assert report.has_failure is True

    report_ok = PyPiPublishReport(results=(r1, r2))
    assert report_ok.has_failure is False


def test_reproducible_build_report() -> None:
    """Test ReproducibleBuildReport all_matched property."""
    r1 = ReproducibleArtifactResult(
        package_name="pkg",
        artifact_name="pkg-1.0.0.whl",
        hash1="abc",
        hash2="abc",
        is_reproducible=True,
    )
    r2 = ReproducibleArtifactResult(
        package_name="pkg",
        artifact_name="pkg-1.0.0.tar.gz",
        hash1="abc",
        hash2="def",
        is_reproducible=False,
    )

    rep_match = ReproducibleBuildReport(epoch="1700000000", results=(r1,))
    assert rep_match.all_matched is True

    rep_mismatch = ReproducibleBuildReport(epoch="1700000000", results=(r1, r2))
    assert rep_mismatch.all_matched is False

    rep_empty = ReproducibleBuildReport(epoch="1700000000", results=())
    assert rep_empty.all_matched is False


def test_pypi_commands_instantiation() -> None:
    """Test instantiation of PyPI CQRS commands."""
    cmd_check = CheckPyPiReleasesCommand(package_name="hexastack-core")
    assert cmd_check.package_name == "hexastack-core"

    cmd_build = BuildPackagesCommand(target_dist=Path("/tmp/dist"))
    assert cmd_build.target_dist == Path("/tmp/dist")

    cmd_pub = PublishPackagesCommand(build_first=True, delay=1.0)
    assert cmd_pub.build_first is True
    assert cmd_pub.delay == 1.0

    cmd_repro = VerifyReproducibleBuildCommand(source_date_epoch="12345")
    assert cmd_repro.source_date_epoch == "12345"
