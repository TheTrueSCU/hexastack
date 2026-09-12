"""Unit tests for SubprocessPyPiRunnerAdapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.adapters.runners.pypi_runner import SubprocessPyPiRunnerAdapter


def test_check_version_exists_found() -> None:
    """Test check_version_exists when version is in releases."""
    adapter = SubprocessPyPiRunnerAdapter(repo_root=Path("/tmp/fake_root"))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"releases": {"1.0.0": []}}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        exists = adapter.check_version_exists("my-pkg", "1.0.0")

    assert exists is True


def test_check_version_exists_not_found_or_error() -> None:
    """Test check_version_exists when version is missing or request fails."""
    adapter = SubprocessPyPiRunnerAdapter(repo_root=Path("/tmp/fake_root"))

    # Missing version
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"releases": {"0.9.0": []}}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        assert adapter.check_version_exists("my-pkg", "1.0.0") is False

    # 404 response
    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp_404
        mock_client_cls.return_value.__enter__.return_value = mock_client

        assert adapter.check_version_exists("my-pkg", "1.0.0") is False

    # Exception
    with patch("httpx.Client", side_effect=RuntimeError("network down")):
        assert adapter.check_version_exists("my-pkg", "1.0.0") is False


def test_build_package_success_and_failure() -> None:
    """Test build_package via uv build."""
    adapter = SubprocessPyPiRunnerAdapter(repo_root=Path("/tmp/fake_root"))

    # Success
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Built wheel", stderr="")
        ok, out = adapter.build_package(
            "my-pkg", Path("/tmp/dist"), env={"SOURCE_DATE_EPOCH": "123"}
        )
        assert ok is True
        assert "Built wheel" in out

    # Failure
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Build error")
        ok, out = adapter.build_package("my-pkg", Path("/tmp/dist"))
        assert ok is False
        assert "Build error" in out


def test_publish_package_outcomes() -> None:
    """Test publish_package classifying outcomes."""
    adapter = SubprocessPyPiRunnerAdapter(repo_root=Path("/tmp/fake_root"))
    files = [Path("/tmp/dist/pkg-1.0.0-py3-none-any.whl")]

    # Success
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        ok, outcome = adapter.publish_package(files, token="token-123")
        assert ok is True
        assert outcome == "published"

    # Rate limited
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="HTTP 429 Too Many Requests"
        )
        ok, outcome = adapter.publish_package(files)
        assert ok is False
        assert outcome == "rate_limited"

    # Already exists
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="File already exists on PyPI"
        )
        ok, outcome = adapter.publish_package(files)
        assert ok is False
        assert outcome == "already_exists"

    # Generic failure
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Invalid auth token"
        )
        ok, outcome = adapter.publish_package(files)
        assert ok is False
        assert outcome == "failed"


def test_get_git_commit_epoch() -> None:
    """Test get_git_commit_epoch."""
    adapter = SubprocessPyPiRunnerAdapter(repo_root=Path("/tmp/fake_root"))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="1700000000\n")
        epoch = adapter.get_git_commit_epoch()
        assert epoch == "1700000000"

    with patch("subprocess.run", side_effect=RuntimeError("git failed")):
        epoch = adapter.get_git_commit_epoch()
        assert epoch is None
