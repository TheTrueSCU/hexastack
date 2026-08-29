"""GitHub Code Scanning Alert Inspector command."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.domain.github import SecurityAlert

console = Console()


def inspect_single_alert(alert_number: int) -> int:
    """Fetch and print detailed remediation panel for a specific alert."""
    with GitHubHttpAdapter() as client:
        alert = client.get_single_alert(alert_number)

    panel_content = (
        f"[bold white]Rule ID:[/bold white] [bold cyan]{alert.rule_id}[/bold cyan]\n"
        f"[bold white]Severity:[/bold white] {alert.severity} ({alert.security_severity_level or 'quality'})\n"
        f"[bold white]Location:[/bold white] [bold blue]{alert.path}:{alert.start_line}-{alert.end_line}[/bold blue]\n"
        f"[bold white]State:[/bold white] {alert.state}\n\n"
        f"[bold white]Message:[/bold white]\n{alert.message}\n\n"
        f"[bold white]Description:[/bold white]\n{alert.rule_description}\n"
    )
    if alert.help_markdown:
        panel_content += f"\n[bold white]Remediation Guidance:[/bold white]\n{alert.help_markdown[:400]}..."

    console.print(
        Panel(
            panel_content,
            title=f"[bold magenta]CodeQL Alert #{alert_number}[/bold magenta]",
            border_style="cyan",
        )
    )
    return 0


def _filter_alerts(
    alerts: list[SecurityAlert],
    rule_filter: str | None,
    package_filter: str | None,
    severity_filter: str | None,
) -> list[SecurityAlert]:
    """Filter list of alerts according to provided criteria."""
    filtered = alerts
    if rule_filter:
        filtered = [a for a in filtered if rule_filter.lower() in a.rule_id.lower()]
    if severity_filter:
        filtered = [
            a for a in filtered if a.severity.lower() == severity_filter.lower()
        ]
    if package_filter:
        filtered = [a for a in filtered if package_filter.lower() in a.path.lower()]
    return filtered


def _build_rule_summary_table(
    by_rule: dict[str, list[SecurityAlert]],
    state: str,
    total_count: int,
) -> Table:
    """Build summary table grouped by rule ID."""
    table = Table(
        title=f"[bold cyan]CodeQL Alerts Summary (State: {state}, Total: {total_count})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rule ID", style="bold")
    table.add_column("Severity", width=12)
    table.add_column("Count", width=8, justify="right")
    table.add_column("Description")

    for rule_id, rule_alerts in sorted(
        by_rule.items(), key=lambda item: len(item[1]), reverse=True
    ):
        sample = rule_alerts[0]
        sev = sample.severity
        if sev in ("error", "critical"):
            sev_styled = f"[bold red]{sev}[/bold red]"
        elif sev == "warning":
            sev_styled = f"[bold yellow]{sev}[/bold yellow]"
        else:
            sev_styled = f"[dim cyan]{sev}[/dim cyan]"

        table.add_row(
            rule_id, sev_styled, str(len(rule_alerts)), sample.rule_description
        )
    return table


def _build_alert_locations_table(alerts: list[SecurityAlert]) -> Table:
    """Build detailed locations table for individual alerts."""
    table = Table(
        title="[bold cyan]Actionable CodeQL Alert Locations & Insights[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Alert #", width=8, style="dim")
    table.add_column("Rule", style="bold")
    table.add_column("Location", style="blue")
    table.add_column("Message / Context")

    for a in sorted(alerts, key=lambda x: x.number, reverse=True):
        table.add_row(f"#{a.number}", a.rule_id, f"{a.path}:{a.start_line}", a.message)
    return table


def inspect_and_bucket_alerts(
    rule_filter: str | None = None,
    package_filter: str | None = None,
    severity_filter: str | None = None,
    state: str = "open",
    show_details: bool = False,
) -> int:
    """Bucket open alerts by rule, severity, and package, displaying actionable tables."""
    with GitHubHttpAdapter() as client:
        raw_alerts = client.get_code_scanning_alerts(state=state)

    if not raw_alerts:
        console.print(
            Panel(
                f"[bold green]🎉 Zero CodeQL code scanning alerts in state '{state}'![/bold green]",
                title="[bold green]Clean Security State[/bold green]",
                border_style="green",
            )
        )
        return 0

    alerts = _filter_alerts(raw_alerts, rule_filter, package_filter, severity_filter)
    if not alerts:
        console.print(
            f"[yellow]No alerts matched the provided filters (rule: '{rule_filter}', pkg: '{package_filter}', sev: '{severity_filter}').[/yellow]"
        )
        return 0

    by_rule: dict[str, list[SecurityAlert]] = defaultdict(list)
    for a in alerts:
        by_rule[a.rule_id].append(a)

    console.print(_build_rule_summary_table(by_rule, state, len(alerts)))
    console.print(_build_alert_locations_table(alerts))

    if show_details:
        for a in sorted(alerts, key=lambda x: x.number, reverse=True):
            inspect_single_alert(a.number)

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
