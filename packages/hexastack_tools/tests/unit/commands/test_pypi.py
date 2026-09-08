"""Unit tests for PyPI build, check, and smart publish tooling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hexastack_tools.commands.pypi import (
    PackageMetadata,
    build_main,
    check_main,
    check_pypi_version_exists,
    publish_main,
    publish_packages,
)


def test_pypi_callables() -> None:
    """Verify pypi distribution callables are valid functions."""
    assert callable(build_main)
    assert callable(check_main)
    assert callable(publish_main)
    assert callable(publish_packages)


def test_check_pypi_version_exists():
    """Verify check_pypi_version_exists handles 200, 404, and exceptions."""
    with patch("httpx.Client.get") as mock_get:
        # 200 with release found
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"releases": {"0.3.5": [{}]}}
        mock_get.return_value = mock_resp
        assert check_pypi_version_exists("hexastack", "0.3.5") is True
        assert check_pypi_version_exists("hexastack", "0.4.0") is False

        # 404 not found
        mock_resp.status_code = 404
        assert check_pypi_version_exists("hexastack-new", "0.1.0") is False

        # Exception
        mock_get.side_effect = Exception("network error")
        assert check_pypi_version_exists("hexastack", "0.3.5") is False


def test_build_main_custom_out_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify build_main parses --out-dir correctly."""
    monkeypatch.setattr("sys.argv", ["pypi-build", "--out-dir", "custom_dist"])
    with patch("hexastack_tools.commands.pypi.build_all_packages") as mock_build:
        mock_build.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            build_main()
        assert exc_info.value.code == 0
        mock_build.assert_called_once_with(out_dir=Path("custom_dist"))


def test_check_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify check_main inspects packages without error."""
    monkeypatch.setattr("sys.argv", ["pypi-check"])
    with (
        patch(
            "hexastack_tools.commands.pypi.get_workspace_packages_metadata"
        ) as mock_pkgs,
        patch(
            "hexastack_tools.commands.pypi.check_pypi_version_exists", return_value=True
        ),
    ):
        mock_pkgs.return_value = [
            PackageMetadata(
                name="hexastack",
                version="0.3.5",
                dir_path=Path("packages/hexastack"),
                pyproject_path=Path("packages/hexastack/pyproject.toml"),
            )
        ]
        check_main()


def test_publish_packages_skip_existing(tmp_path: Path):
    """Verify publish_packages skips packages already on PyPI."""
    pkg = PackageMetadata(
        name="hexastack-core",
        version="0.3.5",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )
    with patch(
        "hexastack_tools.commands.pypi.check_pypi_version_exists", return_value=True
    ):
        rc = publish_packages([pkg], dist_dir=tmp_path, delay=0.0, skip_existing=True)
        assert rc == 0


def test_publish_packages_no_dist_files(tmp_path: Path):
    """Verify publish_packages fails gracefully if dist files are missing."""
    pkg = PackageMetadata(
        name="hexastack-core",
        version="0.3.5",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )
    with patch(
        "hexastack_tools.commands.pypi.check_pypi_version_exists", return_value=False
    ):
        rc = publish_packages([pkg], dist_dir=tmp_path, delay=0.0, skip_existing=True)
        assert rc == 1


def test_publish_packages_success_and_rate_limit(tmp_path: Path):
    """Verify publish_packages handles success, 429 rate limits, and existing errors."""
    dist_file = tmp_path / "hexastack_core-0.4.0-py3-none-any.whl"
    dist_file.touch()

    pkg = PackageMetadata(
        name="hexastack-core",
        version="0.4.0",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )

    # Success upload
    with (
        patch(
            "hexastack_tools.commands.pypi.check_pypi_version_exists",
            return_value=False,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        rc = publish_packages([pkg], dist_dir=tmp_path, token="test-token", delay=0.0)
        assert rc == 0

    # Rate limited upload
    with (
        patch(
            "hexastack_tools.commands.pypi.check_pypi_version_exists",
            return_value=False,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="HTTP 429 Too many new projects created"
        )
        rc = publish_packages([pkg], dist_dir=tmp_path, token="test-token", delay=0.0)
        assert rc == 1

    # Already exists in upload stderr
    with (
        patch(
            "hexastack_tools.commands.pypi.check_pypi_version_exists",
            return_value=False,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="File already exists on PyPI"
        )
        rc = publish_packages([pkg], dist_dir=tmp_path, token="test-token", delay=0.0)
        assert rc == 0


def test_publish_main(monkeypatch: pytest.MonkeyPatch):
    """Verify publish_main CLI entrypoint."""
    monkeypatch.setattr("sys.argv", ["pypi-publish", "--no-build", "--delay", "0.0"])
    with patch("hexastack_tools.commands.pypi.publish_packages", return_value=0):
        with pytest.raises(SystemExit) as exc_info:
            publish_main()
        assert exc_info.value.code == 0
