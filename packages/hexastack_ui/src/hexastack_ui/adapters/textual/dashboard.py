"""Fullscreen interactive terminal operational dashboard built on Textual.

Notes/Architectural Intent:
    Provides a rich Textual terminal user interface (TUI) for inspecting CQRS contracts,
    runtime feature flags, DI container bindings, and middleware execution pipelines
    without web browser or JavaScript dependencies.
"""

from __future__ import annotations

from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_ui.domain.models import DevToolsDashboardState
from hexastack_ui.ports.presenter import DevToolsPresenterPort

__all__ = [
    "check_textual_installed",
    "mount_textual_dashboard",
    "TextualDevToolsApp",
    "TextualDevToolsPresenter",
]


def check_textual_installed() -> None:
    """Verify Textual is available in runtime environment.

    Raises:
        MissingDependencyError: If Textual is not installed.

    Notes/Architectural Intent:
        Enables lazy import error reporting with installation hints.
    """
    try:
        import textual  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError(
            "Textual is required for hexastack-ui Textual support. "
            "Install with 'pip install hexastack-ui[textual]' or 'pip install textual'."
        ) from e


def _create_textual_app_class() -> type:
    """Dynamically construct TextualDevToolsApp when textual is installed."""
    check_textual_installed()
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane

    class _TextualDevToolsApp(App[None]):
        """Textual terminal dashboard inspecting CQRS, feature flags, and DI bindings."""

        TITLE = "Hexastack DevTools Terminal Dashboard"
        SUB_TITLE = "Operational Runtime Inspector"

        BINDINGS = [
            Binding("q", "quit", "Quit", show=True),
            Binding("d", "toggle_dark", "Toggle Dark Mode", show=True),
        ]

        def __init__(
            self,
            state: DevToolsDashboardState | None = None,
            **kwargs: Any,
        ) -> None:
            """Initialize TextualDevToolsApp with optional dashboard state snapshot."""
            super().__init__(**kwargs)
            self.dashboard_state = state or DevToolsDashboardState()

        def compose(self) -> ComposeResult:
            """Compose layout of header, tabs, and tables."""
            yield Header(show_clock=True)
            with TabbedContent(initial="cqrs"):
                with TabPane("CQRS Contracts", id="cqrs"):
                    yield DataTable(id="cqrs-table")
                with TabPane("Feature Flags", id="flags"):
                    yield DataTable(id="flags-table")
                with TabPane("DI Services", id="services"):
                    yield DataTable(id="services-table")
                with TabPane("Middlewares", id="middlewares"):
                    yield DataTable(id="middlewares-table")
            yield Footer()

        def on_mount(self) -> None:
            """Populate data tables upon mounting."""
            self._populate_tables()

        def _populate_tables(self) -> None:
            """Fill tables from current dashboard_state."""
            cqrs_table = self.query_one("#cqrs-table", DataTable)
            cqrs_table.clear(columns=True)
            cqrs_table.add_columns("Message Type", "Name", "Module")
            for cmd in self.dashboard_state.commands:
                cqrs_table.add_row("Command", cmd.name, cmd.module)
            for qry in self.dashboard_state.queries:
                cqrs_table.add_row("Query", qry.name, qry.module)

            flags_table = self.query_one("#flags-table", DataTable)
            flags_table.clear(columns=True)
            flags_table.add_columns("Flag Key", "Status", "Description")
            for flag in self.dashboard_state.flags:
                status = "ENABLED" if flag.enabled else "DISABLED"
                flags_table.add_row(flag.key, status, flag.description)

            services_table = self.query_one("#services-table", DataTable)
            services_table.clear(columns=True)
            services_table.add_columns("Service", "Module", "Resolver")
            for svc in self.dashboard_state.services:
                services_table.add_row(svc.service, svc.module, svc.resolver)

            mw_table = self.query_one("#middlewares-table", DataTable)
            mw_table.clear(columns=True)
            mw_table.add_columns("Order", "Middleware Name")
            for idx, mw in enumerate(self.dashboard_state.middlewares, start=1):
                mw_table.add_row(str(idx), mw)

    return _TextualDevToolsApp


def TextualDevToolsApp(
    state: DevToolsDashboardState | None = None,
    **kwargs: Any,
) -> Any:
    """Construct an instance of TextualDevToolsApp.

    Args:
        state: Optional DevToolsDashboardState snapshot.
        **kwargs: Additional options passed to Textual App.

    Returns:
        Configured Textual App instance.

    Notes/Architectural Intent:
        Lazy factory ensuring Textual is imported only when invoked.
    """
    app_cls = _create_textual_app_class()
    return app_cls(state=state, **kwargs)


def mount_textual_dashboard(
    state: DevToolsDashboardState | None = None,
    **kwargs: Any,
) -> Any:
    """Construct and mount the Textual DevTools dashboard.

    Args:
        state: Optional DevToolsDashboardState snapshot.
        **kwargs: Additional parameters for Textual App.

    Returns:
        Configured Textual App instance.

    Notes/Architectural Intent:
        Provides a functional factory mirroring NiceGUI mount_devtools_dashboard.
    """
    return TextualDevToolsApp(state=state, **kwargs)


class TextualDevToolsPresenter(DevToolsPresenterPort):
    """Terminal UI presenter rendering DevTools dashboards via Textual."""

    def render_dashboard(
        self, state: DevToolsDashboardState, target_app: Any = None, **kwargs: Any
    ) -> None:
        """Render interactive Textual terminal dashboard.

        Args:
            state: Current runtime state snapshot.
            target_app: Optional target application.
            **kwargs: Additional parameters for Textual App.

        Notes/Architectural Intent:
            Launches full-screen terminal TUI loop.
        """
        app = TextualDevToolsApp(state=state, **kwargs)
        app.run()
