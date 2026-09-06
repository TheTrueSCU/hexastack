"""Unit tests for RepoStatus presenter."""

from __future__ import annotations

import json

import pytest
from rich.table import Table

from hexastack_tools.adapters.presenters.repo import (
    build_repo_status_table,
    present_repo_status,
    render_repo_status_json,
    render_repo_status_plain,
)
from hexastack_tools.domain.github import OutputFormat, RepoStatus


@pytest.fixture
def sample_repo_status() -> RepoStatus:
    return RepoStatus(
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
        environments=("github-pages", "pypi"),
        required_status_checks=("CI Success (All Required Checks)",),
        require_conversation_resolution=True,
    )


def test_build_repo_status_table(sample_repo_status: RepoStatus):
    table = build_repo_status_table(sample_repo_status)
    assert isinstance(table, Table)
    assert "TheTrueSCU/hexastack" in str(table.title)


def test_render_repo_status_json(sample_repo_status: RepoStatus):
    raw_json = render_repo_status_json(sample_repo_status)
    data = json.loads(raw_json)
    assert data["name"] == "hexastack"
    assert data["owner"] == "TheTrueSCU"
    assert data["visibility"] == "public"
    assert data["private"] is False
    assert data["allow_auto_merge"] is True
    assert data["can_approve_pull_request_reviews"] is True
    assert data["environments"] == ["github-pages", "pypi"]
    assert data["required_status_checks"] == ["CI Success (All Required Checks)"]
    assert data["require_conversation_resolution"] is True


def test_render_repo_status_plain(sample_repo_status: RepoStatus):
    plain = render_repo_status_plain(sample_repo_status)
    assert "name\thexastack" in plain
    assert "visibility\tpublic" in plain
    assert "environments\tgithub-pages,pypi" in plain
    assert "require_conversation_resolution\tTrue" in plain


def test_present_repo_status_dispatch(
    sample_repo_status: RepoStatus, capsys: pytest.CaptureFixture[str]
):
    # Plain
    present_repo_status(sample_repo_status, output_format=OutputFormat.PLAIN)
    captured_plain = capsys.readouterr()
    assert "owner\tTheTrueSCU" in captured_plain.out

    # JSON
    present_repo_status(sample_repo_status, output_format=OutputFormat.JSON)
    captured_json = capsys.readouterr()
    assert '"visibility": "public"' in captured_json.out

    # Rich
    present_repo_status(sample_repo_status, output_format=OutputFormat.RICH)
    captured_rich = capsys.readouterr()
    assert "GitHub Repository Configuration" in captured_rich.out
