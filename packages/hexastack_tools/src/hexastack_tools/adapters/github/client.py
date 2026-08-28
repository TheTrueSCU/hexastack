"""Concrete adapter implementing GitHubApiPort using httpx and GitHub REST / GraphQL APIs."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import httpx

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PRSummary,
    ReviewComment,
    ReviewThread,
    SecurityAlert,
)
from hexastack_tools.ports.github import GitHubApiPort


def get_github_token() -> str | None:
    """Retrieve GitHub token from environment or gh CLI."""
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


class GitHubHttpAdapter(GitHubApiPort):
    """Adapter executing synchronous HTTP requests to GitHub REST and GraphQL APIs."""

    def __init__(
        self,
        token: str | None = None,
        owner: str = "TheTrueSCU",
        repo: str = "hexastack",
    ) -> None:
        """Initialize GitHub HTTP client adapter.

        Args:
            token: Optional GitHub bearer token.
            owner: Repository owner / organization.
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
        """Close underlying httpx client."""
        self._client.close()

    def __enter__(self) -> GitHubHttpAdapter:
        """Context manager enter."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def get_pr_summary(self, pr_number: int) -> PRSummary:
        """Fetch full aggregate summary for a pull request."""
        resp = self._client.get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}")
        resp.raise_for_status()
        data = resp.json()

        head_ref = data.get("head", {}).get("ref", "")
        head_sha = data.get("head", {}).get("sha", "")

        check_runs = self.get_check_runs(head_sha or head_ref)
        review_threads = self.get_review_threads(pr_number)
        alerts = self.get_code_scanning_alerts(ref=f"refs/pull/{pr_number}/merge")

        # Fetch comments
        comments_resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        )
        general_comments: list[ReviewComment] = []
        if comments_resp.status_code == 200:
            for c in comments_resp.json():
                general_comments.append(
                    ReviewComment(
                        id=c.get("id", 0),
                        author=c.get("user", {}).get("login", "unknown"),
                        body=c.get("body", ""),
                        created_at=c.get("created_at", ""),
                        url=c.get("html_url", ""),
                    )
                )

        return PRSummary(
            number=pr_number,
            title=data.get("title", ""),
            author=data.get("user", {}).get("login", "unknown"),
            state=data.get("state", "open"),
            mergeable=str(data.get("mergeable_state") or "unknown"),
            is_draft=bool(data.get("draft", False)),
            head_ref=head_ref,
            base_ref=data.get("base", {}).get("ref", "main"),
            html_url=data.get("html_url", ""),
            check_runs=tuple(check_runs),
            review_threads=tuple(review_threads),
            security_alerts=tuple(alerts),
            general_comments=tuple(general_comments),
        )

    def get_check_runs(self, ref: str) -> list[CheckRunFinding]:
        """Fetch check runs and commit statuses for a ref."""
        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/commits/{ref}/check-runs"
        )
        if resp.status_code != 200:
            return []

        runs = resp.json().get("check_runs", [])
        findings: list[CheckRunFinding] = []
        for r in runs:
            findings.append(
                CheckRunFinding(
                    name=r.get("name", "unknown"),
                    status=r.get("status", "unknown"),
                    conclusion=r.get("conclusion") or "in_progress",
                    details_url=r.get("html_url") or r.get("details_url", ""),
                    workflow_name=r.get("workflow_name"),
                    started_at=r.get("started_at"),
                    completed_at=r.get("completed_at"),
                )
            )
        return findings

    def get_review_threads(self, pr_number: int) -> list[ReviewThread]:
        """Fetch review discussion threads and conversation resolution state via GraphQL."""
        query = """
        query($owner: String!, $repo: String!, $pr: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $pr) {
              reviewThreads(first: 50) {
                nodes {
                  id
                  isResolved
                  resolvedBy { login }
                  comments(first: 20) {
                    nodes {
                      id
                      body
                      author { login }
                      path
                      line
                      createdAt
                      url
                    }
                  }
                }
              }
            }
          }
        }
        """
        payload = {
            "query": query,
            "variables": {"owner": self.owner, "repo": self.repo, "pr": pr_number},
        }
        resp = self._client.post("/graphql", json=payload)
        if resp.status_code != 200:
            return []

        data = resp.json()
        threads_nodes = (
            data.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
            .get("nodes", [])
        )
        results: list[ReviewThread] = []
        for t in threads_nodes:
            thread_id = t.get("id", "")
            is_resolved = bool(t.get("isResolved", False))
            resolved_by = (
                t.get("resolvedBy", {}).get("login") if t.get("resolvedBy") else None
            )

            comments_list: list[ReviewComment] = []
            for c in t.get("comments", {}).get("nodes", []):
                comments_list.append(
                    ReviewComment(
                        id=c.get("id", ""),
                        author=c.get("author", {}).get("login", "unknown"),
                        body=c.get("body", ""),
                        created_at=c.get("createdAt", ""),
                        path=c.get("path"),
                        line=c.get("line"),
                        url=c.get("url"),
                    )
                )

            results.append(
                ReviewThread(
                    id=thread_id,
                    is_resolved=is_resolved,
                    resolved_by=resolved_by,
                    comments=tuple(comments_list),
                )
            )
        return results

    def get_code_scanning_alerts(
        self,
        ref: str | None = None,
        state: str = "open",
    ) -> list[SecurityAlert]:
        """Fetch CodeQL code scanning alerts."""
        params: dict[str, str] = {"per_page": "100"}
        if state != "all":
            params["state"] = state
        if ref:
            params["ref"] = ref

        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/code-scanning/alerts",
            params=params,
        )
        if resp.status_code != 200:
            return []

        raw_alerts = resp.json()
        if not isinstance(raw_alerts, list):
            return []

        results: list[SecurityAlert] = []
        for a in raw_alerts:
            rule = a.get("rule", {})
            inst = a.get("most_recent_instance", {})
            loc = inst.get("location", {})
            results.append(
                SecurityAlert(
                    number=a.get("number", 0),
                    rule_id=rule.get("id", "unknown"),
                    rule_description=rule.get("description", ""),
                    severity=rule.get("severity", "unknown"),
                    security_severity_level=rule.get("security_severity_level"),
                    state=a.get("state", "open"),
                    path=loc.get("path", "-"),
                    start_line=loc.get("start_line"),
                    end_line=loc.get("end_line"),
                    message=inst.get("message", {}).get("text", ""),
                    help_markdown=rule.get("help"),
                )
            )
        return results

    def get_single_alert(self, alert_number: int) -> SecurityAlert:
        """Fetch full metadata for a single security alert."""
        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/code-scanning/alerts/{alert_number}"
        )
        resp.raise_for_status()
        a = resp.json()

        rule = a.get("rule", {})
        inst = a.get("most_recent_instance", {})
        loc = inst.get("location", {})
        return SecurityAlert(
            number=a.get("number", alert_number),
            rule_id=rule.get("id", "unknown"),
            rule_description=rule.get("description", ""),
            severity=rule.get("severity", "unknown"),
            security_severity_level=rule.get("security_severity_level"),
            state=a.get("state", "open"),
            path=loc.get("path", "-"),
            start_line=loc.get("start_line"),
            end_line=loc.get("end_line"),
            message=inst.get("message", {}).get("text", ""),
            help_markdown=rule.get("help"),
        )


__all__ = [
    "get_github_token",
    "GitHubHttpAdapter",
]
