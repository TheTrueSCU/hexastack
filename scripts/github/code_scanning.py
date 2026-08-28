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


def fetch_open_code_scanning_alerts(
    client: GitHubClient, state: str = "open"
) -> list[dict[str, Any]]:
    """Query GitHub REST API for code scanning alerts.

    Args:
        client: Authenticated GitHubClient instance.
        state: Alert state filter ('open', 'closed', 'dismissed', or 'all').

    Returns:
        List of alert dictionaries.
    """
    params: dict[str, Any] = {"per_page": 100}
    if state != "all":
        params["state"] = state
    resp = client._client.get(
        f"/repos/{client.owner}/{client.repo}/code-scanning/alerts",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def inspect_and_bucket_alerts(
    rule_filter: str | None = None,
    package_filter: str | None = None,
    severity_filter: str | None = None,
    state: str = "open",
    show_details: bool = False,
) -> int:
    """Bucket open alerts by rule, severity, and package, displaying actionable tables.

    Args:
        rule_filter: Optional substring filter for rule ID.
        package_filter: Optional package name substring filter.
        severity_filter: Optional severity level filter.
        state: State filter ('open', 'closed', 'dismissed', or 'all').
        show_details: If True, prints detailed inspection panels for matching alerts.

    Returns:
        0 if clean or alerts displayed, 1 on error.
    """
    with GitHubClient() as client:
        alerts = fetch_open_code_scanning_alerts(client, state=state)

    if not alerts:
        console.print(
            Panel(
                f"[bold green]🎉 Zero CodeQL code scanning alerts in state '{state}'![/bold green]",
                title="[bold green]Clean Security State[/bold green]",
                border_style="green",
            )
        )
        return 0

    # Filter alerts
    if rule_filter:
        alerts = [
            a
            for a in alerts
            if rule_filter.lower() in a.get("rule", {}).get("id", "").lower()
        ]
    if severity_filter:
        alerts = [
            a
            for a in alerts
            if a.get("rule", {}).get("severity", "").lower() == severity_filter.lower()
        ]
    if package_filter:
        alerts = [
            a
            for a in alerts
            if package_filter.lower()
            in a.get("most_recent_instance", {})
            .get("location", {})
            .get("path", "")
            .lower()
        ]

    if not alerts:
        console.print(
            f"[yellow]No alerts matched the provided filters (rule: '{rule_filter}', pkg: '{package_filter}', sev: '{severity_filter}').[/yellow]"
        )
        return 0

    # Group by Rule ID and Package
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
        title=f"[bold cyan]CodeQL Alerts Summary (State: {state}, Total: {len(alerts)})[/bold cyan]",
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

    # 3. Optional inline detailed view
    if show_details:
        for a in sorted(alerts, key=lambda x: x.get("number", 0), reverse=True):
            inspect_single_alert(a["number"])

    return 0


def inspect_single_alert(alert_number: int) -> int:
    """Fetch and print detailed metadata for a single CodeQL alert.

    Args:
        alert_number: The unique alert number.

    Returns:
        0 on success, 1 on error.
    """
    with GitHubClient() as client:
        resp = client._client.get(
            f"/repos/{client.owner}/{client.repo}/code-scanning/alerts/{alert_number}"
        )
        resp.raise_for_status()
        alert = resp.json()

    rule = alert.get("rule", {})
    inst = alert.get("most_recent_instance", {})
    loc = inst.get("location", {})
    path = loc.get("path", "unknown")
    start_line = loc.get("start_line", "-")
    end_line = loc.get("end_line", start_line)
    msg = inst.get("message", {}).get("text", "")
    desc = rule.get("description", "")
    help_text = rule.get("help", "")

    panel_content = (
        f"[bold white]Rule ID:[/bold white] [bold cyan]{rule.get('id', 'unknown')}[/bold cyan]\n"
        f"[bold white]Severity:[/bold white] {rule.get('severity', 'unknown')} ({rule.get('security_severity_level') or 'quality'})\n"
        f"[bold white]Location:[/bold white] [bold blue]{path}:{start_line}-{end_line}[/bold blue]\n"
        f"[bold white]State:[/bold white] {alert.get('state', 'unknown')}\n\n"
        f"[bold white]Message:[/bold white]\n{msg}\n\n"
        f"[bold white]Description:[/bold white]\n{desc}\n"
    )
    if help_text:
        panel_content += (
            f"\n[bold white]Remediation Guidance:[/bold white]\n{help_text[:400]}..."
        )

    console.print(
        Panel(
            panel_content,
            title=f"[bold magenta]CodeQL Alert #{alert_number}[/bold magenta]",
            border_style="cyan",
        )
    )
    return 0


def main() -> int:
    """CLI entrypoint for gh-code-scanning."""
    parser = argparse.ArgumentParser(
        description="Bucket and inspect GitHub CodeQL security & quality code-scanning alerts."
    )
    parser.add_argument(
        "alert",
        nargs="?",
        type=int,
        default=None,
        help="Inspect a specific alert number in detail (e.g. 98).",
    )
    parser.add_argument(
        "--rule",
        "-r",
        type=str,
        default=None,
        help="Filter alerts by rule ID substring (e.g. 'unused-import').",
    )
    parser.add_argument(
        "--package",
        "-p",
        type=str,
        default=None,
        help="Filter alerts by package name substring (e.g. 'hexastack_core').",
    )
    parser.add_argument(
        "--severity",
        "-s",
        type=str,
        default=None,
        help="Filter alerts by severity ('error', 'warning', 'note').",
    )
    parser.add_argument(
        "--state",
        type=str,
        default="open",
        choices=["open", "closed", "dismissed", "all"],
        help="Alert state ('open', 'closed', 'dismissed', 'all').",
    )
    parser.add_argument(
        "--details",
        "-d",
        action="store_true",
        default=False,
        help="Print detailed contextual panels for all matching alerts.",
    )
    args = parser.parse_args()

    try:
        if args.alert is not None:
            return inspect_single_alert(args.alert)

        return inspect_and_bucket_alerts(
            rule_filter=args.rule,
            package_filter=args.package,
            severity_filter=args.severity,
            state=args.state,
            show_details=args.details,
        )

    except Exception as exc:
        console.print(
            f"[bold red]Error querying code scanning alerts:[/bold red] {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
