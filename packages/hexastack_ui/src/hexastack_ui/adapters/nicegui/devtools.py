"""Turnkey DevTools diagnostic dashboard built on NiceGUI.

Notes/Architectural Intent:
    Renders an interactive inspector for CQRS registries, command bus middlewares,
    feature flag state, and DI container service bindings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rodi import Container

from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_ui.adapters.nicegui.page import check_nicegui_installed, mount_ui_app

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = [
    "mount_devtools_dashboard",
]

_STATIC_DIR = Path(__file__).parent / "static"


def _render_cqrs_messages(container: Container) -> None:
    """Render table of registered CQRS message contracts."""
    from nicegui import ui

    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry

    ui.label("Registered CQRS Commands & Queries").classes("hx-section-heading")

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
        ui.label("No CQRS messages registered in container.").classes("hx-empty-label")


def _render_middleware_chain(middlewares: list[Any]) -> None:
    """Render visual chain of active command bus middlewares."""
    from nicegui import ui

    ui.label("Command Bus Middleware Pipeline").classes("hx-section-heading")
    if middlewares:
        with (
            ui.card().classes("hx-card"),
            ui.row().classes("items-center flex-wrap gap-2"),
        ):
            for idx, mw in enumerate(middlewares, 1):
                mw_name = type(mw).__name__
                ui.chip(
                    f"{idx}. {mw_name}",
                    icon="security" if "Auth" in mw_name else "filter_alt",
                    color="blue-9",
                    text_color="white",
                ).classes("font-medium")
                if idx < len(middlewares):
                    ui.icon("arrow_forward", size="sm")
            ui.icon("arrow_forward", size="sm")
            ui.chip(
                "Handler Execution",
                icon="play_circle",
                color="green-9",
                text_color="white",
            ).classes("font-bold")
    else:
        ui.label("No active middlewares attached to CommandBus.").classes(
            "hx-empty-label"
        )


async def _dispatch_ping(
    ping_value: str,
    container: Container,
    pipeline: ExecutionPipeline | None,
    middlewares: list[Any],
    log_output: Any,
) -> None:
    """Execute ping dispatch across pipeline and log output."""
    log_output.push(f"➡️ [DISPATCH] PingDemoCommand(message='{ping_value}')")
    for mw in middlewares:
        log_output.push(
            f"   ↳ [MIDDLEWARE] Intercepting through {type(mw).__name__}..."
        )

    try:
        active_pipeline = pipeline
        if active_pipeline is None and ExecutionPipeline in container:
            active_pipeline = container.resolve(ExecutionPipeline)

        if active_pipeline is not None:
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
                cmd_instance = cmd_cls.model_validate({"message": ping_value})
                res = active_pipeline.execute(cmd_instance)
                log_output.push(f"✅ [SUCCESS] Result: {res}")
            else:
                res = active_pipeline.execute_by_name(
                    "PingDemoCommand", {"message": ping_value}
                )
                log_output.push(f"✅ [SUCCESS] Result: {res}")
        else:
            log_output.push(
                "⚠️ [WARNING] ExecutionPipeline instance not directly bound."
            )
    except Exception as exc:
        log_output.push(f"❌ [ERROR] Execution failed: {exc}")


def _render_live_runner(
    container: Container,
    pipeline: ExecutionPipeline | None,
    middlewares: list[Any],
) -> None:
    """Render interactive test runner card for ping command dispatch."""
    from nicegui import ui

    ui.label("Interactive Pipeline Execution").classes("hx-section-heading")
    with ui.card().classes("hx-card"):
        ui.label("Dispatch PingDemoCommand across the middleware pipeline:").classes(
            "hx-subtext"
        )
        with ui.row().classes("items-center gap-3 w-full"):
            ping_input = ui.input(
                label="Message Payload", value="Hello from Hexastack DevTools!"
            ).classes("flex-grow")
            log_output = ui.log(max_lines=10).classes("hx-log-console")

            async def _run_ping() -> None:
                await _dispatch_ping(
                    str(ping_input.value),
                    container,
                    pipeline,
                    middlewares,
                    log_output,
                )

            ui.button(
                "Dispatch Ping Command", on_click=_run_ping, icon="send", color="blue-9"
            ).classes("text-white font-medium shadow-sm")


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

    ui.label("Active Feature Flags").classes("hx-section-heading")
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
                pagination={"rowsPerPage": 10},
            ).classes("w-full")
        else:
            ui.label("No feature flags currently configured in provider.").classes(
                "hx-empty-label"
            )
    else:
        ui.label(
            "Feature flag provider not available or does not support listing."
        ).classes("hx-empty-label")


def _render_container_tab(container: Container) -> None:
    """Render the DI container tab panel showing registered services."""
    from nicegui import ui

    ui.label("Dependency Injection Services").classes("hx-section-heading")

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
            pagination={"rowsPerPage": 10},
        ).classes("w-full")
    else:
        ui.label("No direct services found in container introspection.").classes(
            "hx-empty-label"
        )


def _render_devtools_content(
    container: Container,
    pipeline: ExecutionPipeline | None,
    title: str,
) -> None:
    """Render the full DevTools dashboard UI components."""
    from nicegui import ui

    ui.add_head_html(
        '<link rel="stylesheet" type="text/css" href="/_hexastack/ui/static/devtools.css">'
    )

    with ui.header().classes("hx-header"):
        with ui.row().classes("hx-header-title"):
            ui.icon("layers", size="md").classes("text-blue-400")
            ui.label(title).classes("hx-header-text")
        ui.badge("v0.3.0", color="blue-10").classes("text-xs font-semibold text-white")

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


def mount_devtools_dashboard(
    app: FastAPI,
    container: Container,
    pipeline: ExecutionPipeline | None = None,
    *,
    path: str = "/_devtools",
    title: str = "Hexastack DevTools",
) -> None:
    """Mount the default Hexastack interactive DevTools dashboard on FastAPI.

    Args:
        app: Target FastAPI application.
        container: Application rodi.Container instance.
        pipeline: Optional ExecutionPipeline instance.
        path: URL path where the dashboard is mounted (default '/_devtools').
        title: Dashboard page title.

    Returns:
        None.

    Raises:
        MissingDependencyError: If NiceGUI is not installed.

    Notes/Architectural Intent:
        Renders a rich developer console inspecting CQRS buses, feature flags,
        and DI container services built entirely using the NiceGUI primitives.
    """
    check_nicegui_installed()
    from nicegui import app as nicegui_app
    from nicegui import ui

    if _STATIC_DIR.is_dir():
        nicegui_app.add_static_files("/_hexastack/ui/static", str(_STATIC_DIR))

    mount_ui_app(app, title=title)

    @ui.page(path, title=title)
    def devtools_page():
        _render_devtools_content(container, pipeline, title)
