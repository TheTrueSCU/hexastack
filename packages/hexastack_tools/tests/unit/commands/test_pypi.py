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
    reproducible_main,
    verify_reproducible_builds,
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


def test_build_main_reproducible_check(monkeypatch: pytest.MonkeyPatch):
    """Verify build_main triggers verify_reproducible_builds when requested."""
    monkeypatch.setattr("sys.argv", ["pypi-build", "--reproducible-check"])
    with (
        patch(
            "hexastack_tools.commands.pypi.verify_reproducible_builds", return_value=0
        ) as mock_repro,
        patch(
            "hexastack_tools.commands.pypi.build_all_packages", return_value=0
        ) as mock_build,
    ):
        with pytest.raises(SystemExit) as exc_info:
            build_main()
        assert exc_info.value.code == 0
        mock_repro.assert_called_once()
        mock_build.assert_called_once()


def test_build_main_reproducible_check_failure(monkeypatch: pytest.MonkeyPatch):
    """Verify build_main aborts when reproducible check fails."""
    monkeypatch.setattr("sys.argv", ["pypi-build", "--reproducible-check"])
    with patch(
        "hexastack_tools.commands.pypi.verify_reproducible_builds", return_value=1
    ):
        with pytest.raises(SystemExit) as exc_info:
            build_main()
        assert exc_info.value.code == 1


def test_verify_reproducible_builds_no_packages():
    """Verify verify_reproducible_builds returns 1 if no packages are found."""
    with patch(
        "hexastack_tools.commands.pypi.get_workspace_packages_metadata", return_value=[]
    ):
        rc = verify_reproducible_builds()
        assert rc == 1


def test_verify_reproducible_builds_success_and_mismatch(tmp_path: Path):
    """Verify verify_reproducible_builds detects matching and mismatching files."""
    pkg = PackageMetadata(
        name="hexastack-core",
        version="0.4.0",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )

    # Success case: fake build outputs matching files
    def fake_build_success(cmd, cwd, env, capture_output, text):
        out_dir = Path(cmd[cmd.index("--out-dir") + 1])
        (out_dir / "hexastack_core-0.4.0-py3-none-any.whl").write_bytes(
            b"exact-content"
        )
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_build_success):
        rc = verify_reproducible_builds([pkg], source_date_epoch="1700000000")
        assert rc == 0

    # Build error case
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        rc = verify_reproducible_builds([pkg], source_date_epoch="1700000000")
        assert rc == 1

    # Mismatch case
    call_count = 0

    def fake_build_mismatch(cmd, cwd, env, capture_output, text):
        nonlocal call_count
        call_count += 1
        out_dir = Path(cmd[cmd.index("--out-dir") + 1])
        (out_dir / "hexastack_core-0.4.0-py3-none-any.whl").write_bytes(
            f"content-{call_count}".encode()
        )
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_build_mismatch):
        rc = verify_reproducible_builds([pkg], source_date_epoch="1700000000")
        assert rc == 1


def test_reproducible_main(monkeypatch: pytest.MonkeyPatch):
    """Verify reproducible_main entrypoint with filtering and missing packages."""
    pkg = PackageMetadata(
        name="hexastack-core",
        version="0.4.0",
        dir_path=Path(),
        pyproject_path=Path("./pyproject.toml"),
    )

    with (
        patch(
            "hexastack_tools.commands.pypi.get_workspace_packages_metadata",
            return_value=[pkg],
        ),
        patch(
            "hexastack_tools.commands.pypi.verify_reproducible_builds", return_value=0
        ) as mock_verify,
    ):
        monkeypatch.setattr("sys.argv", ["pypi-reproducible-check"])
        with pytest.raises(SystemExit) as exc_info:
            reproducible_main()
        assert exc_info.value.code == 0
        mock_verify.assert_called_once()

    # Filter by specific package
    with (
        patch(
            "hexastack_tools.commands.pypi.get_workspace_packages_metadata",
            return_value=[pkg],
        ),
        patch(
            "hexastack_tools.commands.pypi.verify_reproducible_builds", return_value=0
        ) as mock_verify,
    ):
        monkeypatch.setattr(
            "sys.argv", ["pypi-reproducible-check", "-p", "hexastack-core"]
        )
        with pytest.raises(SystemExit) as exc_info:
            reproducible_main()
        assert exc_info.value.code == 0

    # Unknown package
    with patch(
        "hexastack_tools.commands.pypi.get_workspace_packages_metadata",
        return_value=[pkg],
    ):
        monkeypatch.setattr(
            "sys.argv", ["pypi-reproducible-check", "-p", "unknown-pkg"]
        )
        with pytest.raises(SystemExit) as exc_info:
            reproducible_main()
        assert exc_info.value.code == 1
