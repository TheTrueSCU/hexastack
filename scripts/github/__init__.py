"""GitHub API and automation scripts package.

Notes/Architectural Intent:
    Provides direct HTTP-based GitHub API clients, PR check runners, and security audit tools.
"""

from __future__ import annotations

from scripts.github._client import GitHubClient, get_github_token
from scripts.github.checks import inspect_checks
from scripts.github.security import inspect_security_comments

__all__ = [
    "GitHubClient",
    "get_github_token",
    "inspect_checks",
    "inspect_security_comments",
]
