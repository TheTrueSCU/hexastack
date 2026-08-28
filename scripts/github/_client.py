"""Direct GitHub REST & GraphQL API Client.

Notes/Architectural Intent:
    Provides a fast, zero-subprocess HTTP client for GitHub API interactions using
    httpx with token resolution from GITHUB_TOKEN or 'gh auth token'.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import httpx

__all__ = [
    "GitHubClient",
    "get_github_token",
]


def get_github_token() -> str | None:
    """Retrieve GitHub token from environment or gh CLI.

    Returns:
        Token string if discovered, or None.
    """
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token.strip()

    if shutil.which("gh"):
        try:
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return None

    return None


class GitHubClient:
    """Synchronous HTTP client for GitHub REST and GraphQL APIs."""

    def __init__(
        self,
        token: str | None = None,
        owner: str = "TheTrueSCU",
        repo: str = "hexastack",
    ) -> None:
        """Initialize GitHub client with authentication and repo context.

        Args:
            token: Optional GitHub token (discovered if omitted).
            owner: Repository owner/organization name.
            repo: Repository name.
        """
        self.owner = owner
        self.repo = repo
        self.token = token or get_github_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=30.0,
        )

    def close(self) -> None:
        """Close underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> GitHubClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def get_pr(self, pr_number: int) -> dict[str, Any]:
        """Fetch Pull Request details by number.

        Args:
            pr_number: Pull request number.

        Returns:
            Pull request metadata dictionary.
        """
        resp = self._client.get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}")
        resp.raise_for_status()
        return resp.json()

    def list_pr_checks(self, ref: str) -> dict[str, Any]:
        """Fetch check runs and combined commit statuses for a git ref or branch.

        Args:
            ref: Git ref (commit SHA or branch name).

        Returns:
            Dictionary containing 'check_runs' and 'statuses'.
        """
        check_runs_resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/commits/{ref}/check-runs"
        )
        check_runs_resp.raise_for_status()
        check_runs_data = check_runs_resp.json()

        statuses_resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/commits/{ref}/status"
        )
        statuses_resp.raise_for_status()
        statuses_data = statuses_resp.json()

        return {
            "check_runs": check_runs_data.get("check_runs", []),
            "statuses": statuses_data.get("statuses", []),
            "state": statuses_data.get("state", "unknown"),
        }

    def list_pr_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetch inline review comments for a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of review comments.
        """
        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments"
        )
        resp.raise_for_status()
        return resp.json()

    def list_issues(self, state: str = "open", limit: int = 30) -> list[dict[str, Any]]:
        """List repository issues.

        Args:
            state: Filter by issue state ('open', 'closed', 'all').
            limit: Maximum items to return.

        Returns:
            List of issue objects.
        """
        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/issues",
            params={"state": state, "per_page": limit},
        )
        resp.raise_for_status()
        return [item for item in resp.json() if "pull_request" not in item]
