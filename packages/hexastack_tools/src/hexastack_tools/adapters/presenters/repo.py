"""Repository Status Presenter supporting Rich ANSI tables, structured JSON, and plain TSV."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.table import Table

from hexastack_tools.adapters.presenters.common import resolve_output_format
from hexastack_tools.domain.github import OutputFormat, RepoStatus

console = Console()


def build_repo_status_table(status: RepoStatus) -> Table:
    """Construct Rich table for GitHub repository status and governance configuration.

    Args:
        status: RepoStatus domain model.

    Returns:
        Rich Table configured for terminal rendering.
    """
    table = Table(
        title=f"[bold cyan]GitHub Repository Configuration for '{status.owner}/{status.name}'[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Setting", style="bold", width=34)
    table.add_column("Current Value", width=32)
    table.add_column("Notes / Governance Intent", style="dim")

    # Visibility
    vis_style = "green" if not status.private else "yellow"
    table.add_row(
        "Visibility",
        f"[{vis_style}]{status.visibility}[/{vis_style}]",
        "Public repository" if not status.private else "Private repository",
    )

    # Actions Enabled
    act_style = "green" if status.actions_enabled else "red"
    table.add_row(
        "Actions Enabled",
        f'[{act_style}]{status.actions_enabled} (allowed: "{status.allowed_actions}")[/{act_style}]',
        "GitHub Actions CI workflows enabled",
    )

    # Default Workflow Permissions
    wf_style = "green" if status.default_workflow_permissions == "read" else "yellow"
    table.add_row(
        "Default Workflow Permissions",
        f"[{wf_style}]{status.default_workflow_permissions}[/{wf_style}]",
        "Least-Privilege model; individual jobs request explicit write permissions",
    )

    # PR Approval by Actions
    pr_app_style = "green" if status.can_approve_pull_request_reviews else "yellow"
    table.add_row(
        "PR Approval by Actions",
        f"[{pr_app_style}]{status.can_approve_pull_request_reviews}[/{pr_app_style}]",
        "Allows automation workflows (e.g. Dependabot auto-merge) to approve PRs",
    )

    # Allow Squash Merge
    sq_style = "green" if status.allow_squash_merge else "red"
    table.add_row(
        "Allow Squash Merge",
        f"[{sq_style}]{status.allow_squash_merge}[/{sq_style}]",
        "Squash merge strategy enabled for clean commit history",
    )

    # Allow Auto-Merge
    auto_style = "green" if status.allow_auto_merge else "yellow"
    table.add_row(
        "Allow Auto-Merge",
        f"[{auto_style}]{status.allow_auto_merge}[/{auto_style}]",
        "Automated merging enabled when all required checks pass",
    )

    # GitHub Pages
    pages_style = "green" if status.has_pages else "dim"
    table.add_row(
        "GitHub Pages (has_pages)",
        f"[{pages_style}]{status.has_pages}[/{pages_style}]",
        "Zensical documentation static site publishing",
    )

    # Environments
    envs_val = (
        ", ".join(status.environments) if status.environments else "[dim]None[/dim]"
    )
    table.add_row(
        "Environments",
        envs_val,
        f"{len(status.environments)} deployed environment(s)",
    )

    # Required status checks
    checks_val = (
        ", ".join(status.required_status_checks)
        if status.required_status_checks
        else "[dim]None[/dim]"
    )
    table.add_row(
        "Required Status Checks",
        checks_val,
        "Branch protection rules for default branch",
    )

    # Required conversation resolution
    conv_style = "green" if status.require_conversation_resolution else "yellow"
    table.add_row(
        "Require Conversation Resolution",
        f"[{conv_style}]{status.require_conversation_resolution}[/{conv_style}]",
        "All PR review threads must be resolved prior to merge",
    )

    return table


def render_repo_status_json(status: RepoStatus) -> str:
    """Serialize repository status to structured JSON string.

    Args:
        status: RepoStatus model.

    Returns:
        JSON string formatted with 2 spaces indentation.
    """
    data = {
        "owner": status.owner,
        "name": status.name,
        "visibility": status.visibility,
        "private": status.private,
        "default_branch": status.default_branch,
        "allow_auto_merge": status.allow_auto_merge,
        "allow_squash_merge": status.allow_squash_merge,
        "has_pages": status.has_pages,
        "actions_enabled": status.actions_enabled,
        "allowed_actions": status.allowed_actions,
        "default_workflow_permissions": status.default_workflow_permissions,
        "can_approve_pull_request_reviews": status.can_approve_pull_request_reviews,
        "environments": list(status.environments),
        "required_status_checks": list(status.required_status_checks),
        "require_conversation_resolution": status.require_conversation_resolution,
    }
    return json.dumps(data, indent=2)


def render_repo_status_plain(status: RepoStatus) -> str:
    """Serialize repository status into plain TSV format for shell scripting.

    Args:
        status: RepoStatus model.

    Returns:
        TSV string.
    """
    lines = [
        "SETTING\tVALUE",
        f"owner\t{status.owner}",
        f"name\t{status.name}",
        f"visibility\t{status.visibility}",
        f"private\t{status.private}",
        f"default_branch\t{status.default_branch}",
        f"allow_auto_merge\t{status.allow_auto_merge}",
        f"allow_squash_merge\t{status.allow_squash_merge}",
        f"has_pages\t{status.has_pages}",
        f"actions_enabled\t{status.actions_enabled}",
        f"allowed_actions\t{status.allowed_actions}",
        f"default_workflow_permissions\t{status.default_workflow_permissions}",
        f"can_approve_pull_request_reviews\t{status.can_approve_pull_request_reviews}",
        f"environments\t{','.join(status.environments)}",
        f"required_status_checks\t{','.join(status.required_status_checks)}",
        f"require_conversation_resolution\t{status.require_conversation_resolution}",
    ]
    return "\n".join(lines)


def present_repo_status(
    status: RepoStatus,
    output_format: OutputFormat = OutputFormat.AUTO,
) -> None:
    """Display repository status in requested format (rich table, JSON, or TSV).

    Args:
        status: RepoStatus domain model.
        output_format: Target OutputFormat mode.

    Returns:
        None.
    """
    fmt = resolve_output_format(output_format)
    if fmt == OutputFormat.JSON:
        sys.stdout.write(render_repo_status_json(status) + "\n")
    elif fmt == OutputFormat.PLAIN:
        sys.stdout.write(render_repo_status_plain(status) + "\n")
    else:
        table = build_repo_status_table(status)
        console.print(table)


__all__ = [
    "build_repo_status_table",
    "present_repo_status",
    "render_repo_status_json",
    "render_repo_status_plain",
]
