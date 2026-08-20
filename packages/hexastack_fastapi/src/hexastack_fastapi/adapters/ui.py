"""NiceGUI UI presentation adapter and CQRS reactive bindings for Hexastack.

Notes/Architectural Intent:
    Provides reactive UI integration built on NiceGUI and FastAPI:
    1. Primitives: `ui_page`, `dispatch_command`, `dispatch_query`, and reactive hooks
       enabling developers to build custom reactive web applications directly on CQRS.
    2. Default DevTools Dashboard: `mount_devtools_dashboard` providing an out-of-the-box
       interactive inspector for CQRS buses, feature flags, DI container, and metadata.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from rodi import Container

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

if TYPE_CHECKING:
    from hexastack_core.domain import Command, Query

__all__ = [
    "dispatch_command",
    "dispatch_query",
    "mount_devtools_dashboard",
    "mount_ui_app",
    "ui_page",
]


def _check_nicegui_installed() -> None:
    """Verify NiceGUI is available in runtime environment."""
    try:
        import nicegui  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError(
            "NiceGUI is required for hexastack-fastapi UI support. "
            "Install with 'pip install hexastack-fastapi[ui]' or 'pip install nicegui'."
        ) from e


def ui_page(
    path: str,
    *,
    title: str | None = None,
    viewport: str | None = None,
    favicon: str | None = None,
    dark: bool | None = None,
    response_timeout: float = 3.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declarative decorator registering a NiceGUI reactive UI page.

    Notes/Architectural Intent:
        Wraps `nicegui.ui.page` while cleanly decoupling application modules from
        direct NiceGUI hard dependency at module import time.

    Args:
        path: URL path for the page (e.g. '/dashboard', '/users').
        title: Optional browser tab title.
        viewport: Optional viewport meta tag string.
        favicon: Optional favicon path or URL.
        dark: Optional dark mode setting (True/False/None).
        response_timeout: Maximum seconds to wait for client connection response.

    Returns:
        Decorated page function.
    """
    _check_nicegui_installed()
    from nicegui import ui

    return ui.page(
        path,
        title=title,
        viewport=viewport,
        favicon=favicon,
        dark=dark,
        response_timeout=response_timeout,
    )


async def dispatch_command(pipeline: ExecutionPipeline, command: Command) -> Any:
    """Dispatch a CQRS command from a NiceGUI interactive event handler.

    Notes/Architectural Intent:
        Executes a command through the standard ExecutionPipeline,
        supporting synchronous or asynchronous bus handlers.

    Args:
        pipeline: ExecutionPipeline instance.
        command: Command instance to execute.

    Returns:
        Result returned by command execution.
    """
    result = pipeline.execute(command)
    if inspect.isawaitable(result):
        return await result
    return result


async def dispatch_query(pipeline: ExecutionPipeline, query: Query) -> Any:
    """Dispatch a CQRS query from a NiceGUI interactive event handler or data loader.

    Notes/Architectural Intent:
        Executes a query through the standard ExecutionPipeline,
        supporting synchronous or asynchronous bus handlers.

    Args:
        pipeline: ExecutionPipeline instance.
        query: Query instance to execute.

    Returns:
        Result returned by query execution.
    """
    result = pipeline.execute(query)
    if inspect.isawaitable(result):
        return await result
    return result


def mount_ui_app(
    app: FastAPI,
    *,
    title: str = "Hexastack UI",
    viewport: str = "width=device-width, initial-scale=1",
    favicon: str | None = None,
    dark: bool | None = None,
) -> None:
    """Mount NiceGUI reactive engine onto an existing FastAPI application instance.

    Notes/Architectural Intent:
        Integrates NiceGUI's Socket.IO and static assets into the FastAPI lifecycle.

    Args:
        app: Target FastAPI application.
        title: Application default page title.
        viewport: Viewport meta tag.
        favicon: Optional favicon.
        dark: Dark mode preference.

    Returns:
        None.
    """
    _check_nicegui_installed()
    from nicegui import ui

    ui.run_with(
        app,
        title=title,
        viewport=viewport,
        favicon=favicon,
        dark=dark,
    )


def _render_cqrs_messages(container: Container) -> None:
    """Render table of registered CQRS message contracts."""
    from nicegui import ui

    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry

    ui.label("Registered CQRS Commands & Queries").classes("text-lg font-semibold mb-4")

    cmd_reg = (
        container.resolve(CommandRegistry) if CommandRegistry in container else None
    )
    qry_reg = container.resolve(QueryRegistry) if QueryRegistry in container else None

    commands_list = (
        [
            {"type": "Command", "name": getattr(k, "__name__", str(k))}
            for k in cmd_reg.all.values()
        ]
        if cmd_reg
        else []
    )
    queries_list = (
        [
            {"type": "Query", "name": getattr(k, "__name__", str(k))}
            for k in qry_reg.all.values()
        ]
        if qry_reg
        else []
    )
    cqrs_rows = commands_list + queries_list

    if cqrs_rows:
        ui.table(
            columns=[
                {
                    "name": "type",
                    "label": "Message Type",
                    "field": "type",
                    "sortable": True,
                },
                {
                    "name": "name",
                    "label": "Class Name",
                    "field": "name",
                    "sortable": True,
                },
            ],
            rows=cqrs_rows,
            row_key="name",
        ).classes("w-full mb-6")
    else:
        ui.label("No CQRS messages registered in container.").classes(
            "text-slate-500 italic mb-6"
        )


def _render_middleware_chain(middlewares: list[Any]) -> None:
    """Render visual chain of active command bus middlewares."""
    from nicegui import ui

    ui.label("Command Bus Middleware Pipeline").classes("text-lg font-semibold mb-2")
    if middlewares:
        with (
            ui.card().classes("w-full bg-slate-50 dark:bg-slate-900 border p-4 mb-6"),
            ui.row().classes("items-center flex-wrap gap-2"),
        ):
            for idx, mw in enumerate(middlewares, 1):
                mw_name = type(mw).__name__
                ui.chip(
                    f"{idx}. {mw_name}",
                    icon="security" if "Auth" in mw_name else "filter_alt",
                ).classes(
                    "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                )
                if idx < len(middlewares):
                    ui.icon("arrow_forward", size="sm").classes("text-slate-400")
            ui.icon("arrow_forward", size="sm").classes("text-slate-400")
            ui.chip("Handler Execution", icon="play_circle").classes(
                "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200 font-bold"
            )
    else:
        ui.label("No active middlewares attached to CommandBus.").classes(
            "text-slate-500 italic mb-6"
        )


def _render_live_runner(
    container: Container,
    pipeline: ExecutionPipeline | None,
    middlewares: list[Any],
) -> None:
    """Render interactive test runner card for ping command dispatch."""
    from nicegui import ui

    ui.label("Interactive Pipeline Execution").classes("text-lg font-semibold mb-2")
    with ui.card().classes("w-full bg-slate-50 dark:bg-slate-900 border p-4"):
        ui.label("Dispatch PingDemoCommand across the middleware pipeline:").classes(
            "text-sm text-slate-600 dark:text-slate-400 mb-3"
        )
        with ui.row().classes("items-center gap-3 w-full"):
            ping_input = ui.input(
                label="Message Payload", value="Hello from Hexastack DevTools!"
            ).classes("flex-grow")
            log_output = ui.log(max_lines=10).classes(
                "w-full h-32 bg-slate-950 text-emerald-400 p-2 font-mono text-xs rounded border"
            )

            async def _run_ping() -> None:
                log_output.push(
                    f"➡️ [DISPATCH] PingDemoCommand(message='{ping_input.value}')"
                )
                for mw in middlewares:
                    log_output.push(
                        f"   ↳ [MIDDLEWARE] Intercepting through {type(mw).__name__}..."
                    )

                try:
                    active_pipeline = pipeline
                    if active_pipeline is None:
                        from hexastack_cqrs.infra.pipeline import ExecutionPipeline

                        if ExecutionPipeline in container:
                            active_pipeline = container.resolve(ExecutionPipeline)

                    if active_pipeline is not None:
                        # Dynamically find registered command by name matching 'ping'
                        cmd_cls = None
                        from hexastack_cqrs.infra.registries.command import (
                            CommandRegistry,
                        )

                        if CommandRegistry in container:
                            creg = container.resolve(CommandRegistry)
                            for name, cls in creg.all.items():
                                if "ping" in name.lower():
                                    cmd_cls = cls
                                    break

                        if cmd_cls is not None:
                            cmd_instance = cmd_cls.model_validate(
                                {"message": ping_input.value}
                            )
                            res = active_pipeline.execute(cmd_instance)
                            log_output.push(f"✅ [SUCCESS] Result: {res}")
                        else:
                            # Fallback to execute_by_name directly
                            res = active_pipeline.execute_by_name(
                                "PingDemoCommand", {"message": ping_input.value}
                            )
                            log_output.push(f"✅ [SUCCESS] Result: {res}")
                    else:
                        log_output.push(
                            "⚠️ [WARNING] ExecutionPipeline instance not directly bound."
                        )
                except Exception as exc:
                    log_output.push(f"❌ [ERROR] Execution failed: {exc}")

            ui.button("Dispatch Ping Command", on_click=_run_ping, icon="send").classes(
                "bg-blue-600 text-white"
            )


def _render_cqrs_tab(
    container: Container, pipeline: ExecutionPipeline | None = None
) -> None:
    """Render the CQRS tab panel showing registered messages, middleware pipeline, and live runner."""
    from hexastack_cqrs.ports.buses import CommandBusPort

    _render_cqrs_messages(container)
    cmd_bus = container.resolve(CommandBusPort) if CommandBusPort in container else None
    middlewares = getattr(cmd_bus, "_middleware", []) if cmd_bus else []
    _render_middleware_chain(middlewares)
    _render_live_runner(container, pipeline, middlewares)


def _render_flags_tab(container: Container) -> None:
    """Render the feature flags tab panel showing active flags."""
    from nicegui import ui

    from hexastack_core.ports.feature_flags import FeatureFlagPort

    ui.label("Active Feature Flags").classes("text-lg font-semibold mb-4")
    flags_adapter = (
        container.resolve(FeatureFlagPort) if FeatureFlagPort in container else None
    )

    get_all_fn = getattr(flags_adapter, "get_all_flags", None)
    if callable(get_all_fn):
        flags_data: dict[str, Any] = get_all_fn()
        if flags_data:
            flag_rows = [{"flag": k, "enabled": str(v)} for k, v in flags_data.items()]
            ui.table(
                columns=[
                    {
                        "name": "flag",
                        "label": "Flag Key",
                        "field": "flag",
                        "sortable": True,
                    },
                    {
                        "name": "enabled",
                        "label": "Status",
                        "field": "enabled",
                        "sortable": True,
                    },
                ],
                rows=flag_rows,
                row_key="flag",
            ).classes("w-full")
        else:
            ui.label("No feature flags currently configured in provider.").classes(
                "text-slate-500 italic"
            )
    else:
        ui.label(
            "Feature flag provider not available or does not support listing."
        ).classes("text-slate-500 italic")


def _render_container_tab(container: Container) -> None:
    """Render the DI container tab panel showing registered services."""
    from nicegui import ui

    ui.label("Dependency Injection Services").classes("text-lg font-semibold mb-4")

    # rodi.Container stores service registrations in `_map`
    service_map = getattr(container, "_map", {})
    services: list[dict[str, str]] = []

    for cls, resolver in service_map.items():
        service_name = getattr(cls, "__qualname__", getattr(cls, "__name__", str(cls)))
        module_name = getattr(cls, "__module__", "")
        resolver_desc = str(resolver).strip("<>")

        services.append(
            {
                "service": service_name,
                "module": module_name,
                "resolver": resolver_desc,
            }
        )

    # Sort services alphabetically by service name
    services.sort(key=lambda s: s["service"])

    if services:
        ui.table(
            columns=[
                {
                    "name": "service",
                    "label": "Registered Port / Service",
                    "field": "service",
                    "sortable": True,
                },
                {
                    "name": "module",
                    "label": "Module",
                    "field": "module",
                    "sortable": True,
                },
                {
                    "name": "resolver",
                    "label": "Binding / Lifetime",
                    "field": "resolver",
                    "sortable": True,
                },
            ],
            rows=services,
            row_key="service",
        ).classes("w-full")
    else:
        ui.label("No direct services found in container introspection.").classes(
            "text-slate-500 italic"
        )


def mount_devtools_dashboard(
    app: FastAPI,
    container: Container,
    pipeline: ExecutionPipeline | None = None,
    *,
    path: str = "/_devtools",
    title: str = "Hexastack DevTools",
) -> None:
    """Mount the default Hexastack interactive DevTools dashboard on FastAPI.

    Notes/Architectural Intent:
        Renders a rich developer console inspecting CQRS buses, feature flags,
        and DI container services built entirely using the NiceGUI primitives.

    Args:
        app: Target FastAPI application.
        container: Application rodi.Container instance.
        pipeline: Optional ExecutionPipeline instance.
        path: URL path where the dashboard is mounted (default '/_devtools').
        title: Dashboard page title.

    Returns:
        None.
    """
    _check_nicegui_installed()
    from nicegui import ui

    mount_ui_app(app, title=title)

    @ui.page(path, title=title)
    def devtools_page():
        ui.colors(primary="#3B82F6", secondary="#10B981", accent="#8B5CF6")

        with ui.header().classes(
            "items-center justify-between bg-slate-900 text-white px-6 py-3"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("layers", size="md").classes("text-blue-400")
                ui.label(title).classes("text-xl font-bold tracking-tight")
            ui.badge("v0.1.0", color="blue").classes("text-xs")

        with ui.tabs().classes("w-full bg-slate-100 dark:bg-slate-800") as tabs:
            tab_cqrs = ui.tab("CQRS Registry", icon="bolt")
            tab_flags = ui.tab("Feature Flags", icon="toggle_on")
            tab_container = ui.tab("DI Container", icon="hub")

        with ui.tab_panels(tabs, value=tab_cqrs).classes("w-full p-6"):
            with ui.tab_panel(tab_cqrs):
                _render_cqrs_tab(container, pipeline=pipeline)

            with ui.tab_panel(tab_flags):
                _render_flags_tab(container)

            with ui.tab_panel(tab_container):
                _render_container_tab(container)
