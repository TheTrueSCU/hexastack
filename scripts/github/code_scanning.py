"""GitHub Code Scanning Alert Inspector & Automated Refactoring Tool.

Notes/Architectural Intent:
    Fetches open CodeQL security and quality code-scanning alerts via GitHubClient,
    buckets alerts by rule ID, subsystem/package, and severity, and provides
    actionable insights and programmatic refactoring helpers.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.github._client import GitHubClient

__all__ = [
    "fetch_open_code_scanning_alerts",
    "inspect_and_bucket_alerts",
    "main",
]

console = Console()


def fetch_open_code_scanning_alerts(client: GitHubClient) -> list[dict[str, Any]]:
    """Query GitHub REST API for all open code scanning alerts.

    Args:
        client: Authenticated GitHubClient instance.

    Returns:
        List of alert dictionaries.
    """
    resp = client._client.get(
        f"/repos/{client.owner}/{client.repo}/code-scanning/alerts",
        params={"state": "open", "per_page": 100},
    )
    resp.raise_for_status()
    return resp.json()


def inspect_and_bucket_alerts(rule_filter: str | None = None) -> int:
    """Bucket open alerts by rule, severity, and package, displaying actionable tables.

    Args:
        rule_filter: Optional substring filter for rule ID.

    Returns:
        0 if clean or alerts displayed, 1 on error.
    """
    with GitHubClient() as client:
        alerts = fetch_open_code_scanning_alerts(client)

    if not alerts:
        console.print(
            Panel(
                "[bold green]🎉 Zero open CodeQL code-scanning alerts found![/bold green]",
                title="[bold cyan]CodeQL Code Scanning Status[/bold cyan]",
            )
        )
        return 0

    if rule_filter:
        alerts = [
            a
            for a in alerts
            if rule_filter.lower() in a.get("rule", {}).get("id", "").lower()
        ]

    # Groupings
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_package: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for a in alerts:
        rule_id = a.get("rule", {}).get("id", "unknown")
        loc = a.get("most_recent_instance", {}).get("location", {})
        path = loc.get("path", "unknown")

        # Determine package
        if path.startswith("packages/"):
            parts = path.split("/")
            pkg_name = parts[1] if len(parts) > 1 else "packages"
        else:
            pkg_name = path.split("/")[0] if "/" in path else "root"

        by_rule[rule_id].append(a)
        by_package[pkg_name].append(a)

    # 1. Summary by Rule Table
    summary_table = Table(
        title=f"[bold cyan]CodeQL Open Alerts Summary (Total: {len(alerts)})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    summary_table.add_column("Rule ID", style="bold")
    summary_table.add_column("Severity", width=12)
    summary_table.add_column("Count", width=8, justify="right")
    summary_table.add_column("Description")

    for rule_id, rule_alerts in sorted(
        by_rule.items(), key=lambda item: len(item[1]), reverse=True
    ):
        sample = rule_alerts[0]
        sev = sample.get("rule", {}).get("severity", "unknown")
        desc = sample.get("rule", {}).get("description", "")

        if sev in ("error", "critical"):
            sev_styled = f"[bold red]{sev}[/bold red]"
        elif sev == "warning":
            sev_styled = f"[bold yellow]{sev}[/bold yellow]"
        else:
            sev_styled = f"[dim cyan]{sev}[/dim cyan]"

        summary_table.add_row(rule_id, sev_styled, str(len(rule_alerts)), desc)

    console.print(summary_table)

    # 2. Detailed Findings by Location
    detail_table = Table(
        title="[bold cyan]Actionable CodeQL Alert Locations & Insights[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    detail_table.add_column("Alert #", width=8, style="dim")
    detail_table.add_column("Rule", style="bold")
    detail_table.add_column("Location", style="blue")
    detail_table.add_column("Message / Context")

    for a in sorted(alerts, key=lambda x: x.get("number", 0), reverse=True):
        num = str(a.get("number", "-"))
        rule = a.get("rule", {}).get("id", "")
        inst = a.get("most_recent_instance", {})
        loc = inst.get("location", {})
        path = loc.get("path", "-")
        line = loc.get("start_line", "-")
        msg = inst.get("message", {}).get("text", "")

        detail_table.add_row(f"#{num}", rule, f"{path}:{line}", msg)

    console.print(detail_table)
    return 0


def main() -> int:
    """CLI entrypoint for gh-code-scanning."""
    parser = argparse.ArgumentParser(
        description="Bucket and inspect GitHub CodeQL security & quality code-scanning alerts."
    )
    parser.add_argument(
        "--rule",
        "-r",
        type=str,
        default=None,
        help="Filter alerts by rule ID substring (e.g. 'ineffectual-statement').",
    )
    args = parser.parse_args()

    try:
        return inspect_and_bucket_alerts(rule_filter=args.rule)
    except Exception as exc:
        console.print(
            f"[bold red]Error querying code scanning alerts:[/bold red] {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
