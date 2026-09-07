"""Concrete adapter implementing GitHubApiPort using httpx and GitHub REST / GraphQL APIs."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import httpx

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PrSummary,
    RepoStatus,
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


def _parse_github_url(url: str) -> tuple[str, str] | None:
    """Parse owner and repo name from a git remote URL string."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4].rstrip("/")

    # Handle SSH SCP-style: git@github.com:Owner/Repo
    if cleaned.startswith(("git@github.com:", "git@api.github.com:")):
        path_part = cleaned.split(":", 1)[1]
        parts = path_part.strip("/").split("/")
        return (parts[0], parts[1]) if len(parts) == 2 else None

    # Handle HTTP/HTTPS/SSH URLs: https://github.com/Owner/Repo, https://token@github.com/Owner/Repo
    from urllib.parse import urlparse

    parsed = urlparse(cleaned)
    if parsed.hostname in ("github.com", "www.github.com", "api.github.com"):
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None


def get_current_repo() -> tuple[str, str]:
    """Derive owner and repository name from git remote or defaults."""
    if not shutil.which("git"):
        return "TheTrueSCU", "hexastack"

    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            parsed = _parse_github_url(res.stdout.strip())
            if parsed:
                return parsed
    except (subprocess.SubprocessError, OSError):
        # Fall back to default repo if git command execution fails
        pass

    return "TheTrueSCU", "hexastack"


class GitHubHttpAdapter(GitHubApiPort):
    """Adapter executing synchronous HTTP requests to GitHub REST and GraphQL APIs."""

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ) -> None:
        """Initialize GitHub HTTP client adapter.

        Args:
            token: Optional GitHub bearer token.
            owner: Repository owner / organization (defaults to local git checkout origin).
            repo: Repository name (defaults to local git checkout origin).
        """
        default_owner, default_repo = get_current_repo()
        self.owner = owner or default_owner
        self.repo = repo or default_repo
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

    def get_repo_status(
        self,
        owner: str | None = None,
        repo: str | None = None,
    ) -> RepoStatus:
        """Fetch repository configuration, settings, permissions, and environments.

        Args:
            owner: Optional repository owner (defaults to adapter config).
            repo: Optional repository name (defaults to adapter config).

        Returns:
            RepoStatus domain model.
        """
        target_owner = owner or self.owner
        target_repo = repo or self.repo

        # 1. Main repo metadata
        resp_repo = self._client.get(f"/repos/{target_owner}/{target_repo}")
        resp_repo.raise_for_status()
        data_repo = resp_repo.json()

        # 2. Actions permissions
        resp_act = self._client.get(
            f"/repos/{target_owner}/{target_repo}/actions/permissions"
        )
        data_act = resp_act.json() if resp_act.status_code == 200 else {}

        # 3. Actions workflow permissions
        resp_wf = self._client.get(
            f"/repos/{target_owner}/{target_repo}/actions/permissions/workflow"
        )
        data_wf = resp_wf.json() if resp_wf.status_code == 200 else {}

        # 4. Environments
        resp_env = self._client.get(f"/repos/{target_owner}/{target_repo}/environments")
        envs_list: list[str] = []
        if resp_env.status_code == 200:
            envs_list = [
                e.get("name", "")
                for e in resp_env.json().get("environments", [])
                if e.get("name")
            ]

        # 5. Branch protection for default branch
        default_branch = data_repo.get("default_branch", "main")
        resp_prot = self._client.get(
            f"/repos/{target_owner}/{target_repo}/branches/{default_branch}/protection"
        )
        required_checks: list[str] = []
        require_conv_res = False
        if resp_prot.status_code == 200:
            data_prot = resp_prot.json()
            required_checks = data_prot.get("required_status_checks", {}).get(
                "contexts", []
            )
            require_conv_res = bool(
                data_prot.get("required_conversation_resolution", {}).get(
                    "enabled", False
                )
            )

        return RepoStatus(
            name=data_repo.get("name", target_repo),
            owner=target_owner,
            visibility=data_repo.get(
                "visibility", "public" if not data_repo.get("private") else "private"
            ),
            private=bool(data_repo.get("private", False)),
            default_branch=default_branch,
            allow_auto_merge=bool(data_repo.get("allow_auto_merge", False)),
            allow_squash_merge=bool(data_repo.get("allow_squash_merge", True)),
            has_pages=bool(data_repo.get("has_pages", False)),
            actions_enabled=bool(data_act.get("enabled", True)),
            allowed_actions=str(data_act.get("allowed_actions", "all")),
            default_workflow_permissions=str(
                data_wf.get("default_workflow_permissions", "read")
            ),
            can_approve_pull_request_reviews=bool(
                data_wf.get("can_approve_pull_request_reviews", False)
            ),
            environments=tuple(envs_list),
            required_status_checks=tuple(required_checks),
            require_conversation_resolution=require_conv_res,
        )

    def get_pr_summary(self, pr_number: int) -> PrSummary:
        """Fetch full aggregate summary for a pull request."""
        resp = self._client.get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}")
        resp.raise_for_status()
        data = resp.json()

        head_ref = data.get("head", {}).get("ref", "")
        head_sha = data.get("head", {}).get("sha", "")

        check_runs = self.get_check_runs(head_sha or head_ref)
        review_threads = self.get_review_threads(pr_number)
        alerts = self.get_code_scanning_alerts(ref=f"refs/pull/{pr_number}/merge")

        # Fetch issue comments
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
                        is_review_comment=False,
                    )
                )

        # Fetch inline review comments (including CodeQL and code reviews)
        pull_comments_resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments"
        )
        if pull_comments_resp.status_code == 200:
            for c in pull_comments_resp.json():
                general_comments.append(
                    ReviewComment(
                        id=c.get("id", 0),
                        author=c.get("user", {}).get("login", "unknown"),
                        body=c.get("body", ""),
                        created_at=c.get("created_at", ""),
                        path=c.get("path"),
                        line=c.get("line") or c.get("original_line"),
                        url=c.get("html_url", ""),
                        diff_hunk=c.get("diff_hunk"),
                        is_review_comment=True,
                    )
                )

        return PrSummary(
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

    def get_failed_run_logs(self, run_id: int | str) -> str | None:
        """Fetch failed log output for a workflow run using gh CLI or REST API."""
        if shutil.which("gh"):
            try:
                res = subprocess.run(
                    ["gh", "run", "view", str(run_id), "--log-failed"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                # Ignore subprocess failure when retrieving failed run logs via gh CLI
                pass

        return None

    def get_workflow_runs(
        self,
        branch: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch recent workflow runs for a branch."""
        if shutil.which("gh"):
            cmd = [
                "gh",
                "run",
                "list",
                "--json",
                "databaseId,name,conclusion,headSha,event,status,displayTitle,url",
                "--limit",
                str(limit),
            ]
            if branch:
                cmd.extend(["--branch", branch])
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0 and res.stdout.strip():
                    import json

                    return json.loads(res.stdout.strip())
            except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
                # Fall back to GitHub REST API if local gh CLI execution fails
                pass

        params: dict[str, Any] = {"per_page": limit}
        if branch:
            params["branch"] = branch
        resp = self._client.get(
            f"/repos/{self.owner}/{self.repo}/actions/runs", params=params
        )
        if resp.status_code != 200:
            return []
        data = resp.json().get("workflow_runs", [])
        return [
            {
                "databaseId": r.get("id"),
                "name": r.get("name"),
                "conclusion": r.get("conclusion") or "",
                "headSha": r.get("head_sha", ""),
                "event": r.get("event", ""),
                "status": r.get("status", ""),
                "displayTitle": r.get("display_title", ""),
                "url": r.get("html_url", ""),
            }
            for r in data
        ]


__all__ = [
    "get_github_token",
    "GitHubHttpAdapter",
]
