"""Unit tests for gh-repo CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexastack_tools.commands.repo import app
from hexastack_tools.domain.github import RepoStatus

runner = CliRunner()


@patch("hexastack_tools.commands.repo.GitHubHttpAdapter")
def test_gh_repo_command_default(mock_adapter_cls):
    mock_instance = MagicMock()
    mock_adapter_cls.return_value.__enter__.return_value = mock_instance

    mock_instance.get_repo_status.return_value = RepoStatus(
        name="hexastack",
        owner="TheTrueSCU",
        visibility="public",
        private=False,
        default_branch="main",
        allow_auto_merge=True,
        allow_squash_merge=True,
        has_pages=True,
        actions_enabled=True,
        allowed_actions="all",
        default_workflow_permissions="read",
        can_approve_pull_request_reviews=True,
        environments=("github-pages",),
        required_status_checks=("CI",),
        require_conversation_resolution=True,
    )

    result = runner.invoke(app, ["--format", "plain"])
    assert result.exit_code == 0
    assert "owner\tTheTrueSCU" in result.output
    assert "name\thexastack" in result.output


@patch("hexastack_tools.commands.repo.GitHubHttpAdapter")
def test_gh_repo_command_custom_repo(mock_adapter_cls):
    mock_instance = MagicMock()
    mock_adapter_cls.return_value.__enter__.return_value = mock_instance

    mock_instance.get_repo_status.return_value = RepoStatus(
        name="hexaqueue",
        owner="TheTrueSCU",
        visibility="private",
        private=True,
        default_branch="main",
        allow_auto_merge=False,
        allow_squash_merge=True,
        has_pages=False,
        actions_enabled=True,
        allowed_actions="all",
        default_workflow_permissions="read",
        can_approve_pull_request_reviews=True,
        environments=("github-pages",),
        required_status_checks=(),
        require_conversation_resolution=False,
    )

    result = runner.invoke(app, ["TheTrueSCU/hexaqueue", "--format", "json"])
    assert result.exit_code == 0
    assert '"name": "hexaqueue"' in result.output
    assert '"private": true' in result.output


@patch("hexastack_tools.commands.repo.GitHubHttpAdapter")
def test_gh_repo_command_error(mock_adapter_cls):
    mock_instance = MagicMock()
    mock_adapter_cls.return_value.__enter__.return_value = mock_instance
    mock_instance.get_repo_status.side_effect = RuntimeError("API error")

    result = runner.invoke(app, ["--format", "json"])
    assert result.exit_code == 1
    assert "Error querying GitHub repository status" in result.output
