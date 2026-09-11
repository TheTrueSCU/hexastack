"""Rich presenter adapter for governance verification reports.

Notes/Architectural Intent:
    Renders terminal dashboard summary tables and diagnostic panels for code
    quality, static analysis, and test battery outcomes using Rich.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.governance import (
    CheckStatus,
    SanityCheckReport,
)
from hexastack_tools.ports.governance import GovernancePresenterPort

__all__ = [
    "RichGovernancePresenterAdapter",
]


class RichGovernancePresenterAdapter(GovernancePresenterPort):
    """Rich console presenter implementing GovernancePresenterPort."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
        """Render sanity check results table and diagnostics.

        Args:
            report: Aggregated SanityCheckReport object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """
        table = Table(
            title="Hexastack Scoped Sanity Check Dashboard",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Check", style="bold", ratio=2)
        table.add_column("Target", style="magenta", ratio=2)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Duration", justify="right", ratio=1)
        table.add_column("Details", style="dim", ratio=4)

        for res in report.results:
            status_style = {
                CheckStatus.PASS: "[bold green]✅ PASS[/bold green]",
                CheckStatus.FAIL: "[bold red]❌ FAIL[/bold red]",
                CheckStatus.SKIP: "[yellow]⏭️ SKIP[/yellow]",
            }.get(res.status, str(res.status.value))

            table.add_row(
                res.check_name,
                res.target_name,
                status_style,
                f"{res.duration:.2f}s",
                res.details,
            )

        self._console.print()
        self._console.print(table)

        # Print error details panels for failures
        failures = [r for r in report.results if r.status == CheckStatus.FAIL]
        for f in failures:
            if f.error_output:
                self._console.print(
                    Panel(
                        f.error_output,
                        title=f"[bold red]❌ {f.check_name} Failure ({f.target_name})[/bold red]",
                        border_style="red",
                    )
                )

        if failures:
            self._console.print(
                Panel(
                    f"[bold red]❌ {len(failures)} check(s) failed in {report.total_duration:.2f}s.[/bold red]\n"
                    "Fix reported errors or run with [bold cyan]--fix[/bold cyan] where supported.",
                    border_style="red",
                )
            )
        else:
            self._console.print(
                Panel(
                    f"[bold green]✨ All {len(report.results)} sanity checks passed in {report.total_duration:.2f}s![/bold green]",
                    border_style="green",
                )
            )

        return report.exit_code
