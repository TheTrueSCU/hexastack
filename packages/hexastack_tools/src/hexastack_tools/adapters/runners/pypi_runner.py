"""Subprocess and HTTP execution adapter for PyPI operations.

Notes/Architectural Intent:
    Encapsulates HTTP requests to PyPI JSON index, uv build/publish CLI invocations,
    and Git timestamp extraction behind the PyPiClientPort interface.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx

from hexastack_tools.ports.pypi import PyPiClientPort
from hexastack_tools.utils.workspace import get_repo_root

__all__ = [
    "SubprocessPyPiRunnerAdapter",
]


class SubprocessPyPiRunnerAdapter(PyPiClientPort):
    """Execution adapter implementing PyPiClientPort via HTTP requests and CLI subprocesses."""

    def __init__(self, repo_root: Path | None = None) -> None:
        """Initialize adapter with repository root directory.

        Args:
            repo_root: Root workspace path (defaults to auto-discovered repo root).

        Notes/Architectural Intent:
            Keeps subprocess operations anchored to the workspace root.
        """
        self._repo_root = repo_root or get_repo_root()

    def check_version_exists(self, package_name: str, version: str) -> bool:
        """Check if a specific package version is already released on PyPI.

        Args:
            package_name: Name of the distribution package.
            version: Version string to query.

        Returns:
            True if package version exists on PyPI, False otherwise.

        Notes/Architectural Intent:
            Queries public PyPI JSON API with a timeout to avoid hanging on slow network.
        """
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    releases = data.get("releases", {})
                    return version in releases
                return False
        except Exception:
            return False

    def build_package(
        self,
        package_name: str,
        out_dir: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Build distribution package artifacts (wheel and sdist) via uv build.

        Args:
            package_name: Name of workspace package to build.
            out_dir: Destination directory for built artifacts.
            env: Optional environment variables dictionary (e.g. SOURCE_DATE_EPOCH).

        Returns:
            Tuple of (success: bool, output: str).

        Notes/Architectural Intent:
            Executes uv build subprocess within the repository root context.
        """
        cmd = ["uv", "build", "--package", package_name, "--out-dir", str(out_dir)]
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        res = subprocess.run(
            cmd,
            cwd=self._repo_root,
            env=run_env,
            capture_output=True,
            text=True,
        )
        output = res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
        return res.returncode == 0, output

    def publish_package(
        self,
        files: list[Path],
        token: str | None = None,
    ) -> tuple[bool, str]:
        """Publish distribution artifacts to PyPI via uv publish.

        Args:
            files: List of file paths to upload.
            token: Optional PyPI API upload token.

        Returns:
            Tuple of (success: bool, outcome_or_error: str).

        Notes/Architectural Intent:
            Parses CLI response strings to classify outcomes (published, rate_limited, already_exists).
        """
        cmd = ["uv", "publish"]
        if token:
            cmd.extend(["--token", token])
        cmd.extend([str(f) for f in files])

        res = subprocess.run(
            cmd,
            cwd=self._repo_root,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return True, "published"

        err_msg = res.stderr or res.stdout
        err_lower = err_msg.lower()
        if "429" in err_msg or "too many" in err_lower or "rate limit" in err_lower:
            return False, "rate_limited"
        if "already exists" in err_lower or "file already exists" in err_lower:
            return False, "already_exists"
        return False, "failed"

    def get_git_commit_epoch(self) -> str | None:
        """Fetch latest git commit timestamp for reproducible build timestamping.

        Returns:
            Epoch string or None if not accessible.

        Notes/Architectural Intent:
            Used as default SOURCE_DATE_EPOCH for byte-for-byte reproducible build verification.
        """
        try:
            res = subprocess.run(
                ["git", "log", "-1", "--pretty=%ct"],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return res.stdout.strip() or None
        except Exception:
            return None
