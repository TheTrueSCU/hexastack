"""Turnkey DevTools diagnostic dashboard built on NiceGUI.

Notes/Architectural Intent:
    Renders an interactive inspector for CQRS registries, command bus middlewares,
    feature flag state, and DI container service bindings.
"""

from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rodi import Container

from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_ui.adapters.nicegui.page import check_nicegui_installed, mount_ui_app

if TYPE_CHECKING:
    from fastapi import FastAPI

_fallback_logger = logging.getLogger(__name__)

__all__ = [
    "generate_topology_mermaid",
    "mount_devtools_dashboard",
]


def _resolve_static_dir() -> Path | None:
    """Resolve static asset directory using PEP 451/616 importlib.resources.

    Returns:
        Path to static directory if present, else None.
    """
    try:
        traversable = importlib.resources.files(
            "hexastack_ui.adapters.nicegui"
        ).joinpath("static")
        if traversable.is_dir():
            if isinstance(traversable, Path):
                return traversable
            candidate = Path(str(traversable))
            if candidate.is_dir():
                return candidate
    except (TypeError, FileNotFoundError, ModuleNotFoundError) as exc:
        _fallback_logger.debug(
            "Could not resolve static dir via importlib.resources: %s", exc
        )
    fallback = Path(__file__).parent / "static"
    return fallback if fallback.is_dir() else None


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


def _render_observability_tab(container: Container) -> None:
    """Render telemetry, structured logging, and Sentry observability status."""
    import os

    from nicegui import ui

    from hexastack_core.ports.logging import LoggingPort

    ui.label("Telemetry & Observability").classes("hx-section-heading")
    ui.label(
        "Real-time diagnostic health and remote error reporting configuration."
    ).classes("hx-subtext")

    logger = container.resolve(LoggingPort) if LoggingPort in container else None
    is_sentry = hasattr(logger, "is_connected") or (
        logger is not None and "Sentry" in type(logger).__name__
    )
    is_connected = bool(getattr(logger, "is_connected", False)) if is_sentry else False
    masked_dsn = getattr(logger, "masked_dsn", None)
    if not masked_dsn and os.getenv("SENTRY_DSN"):
        raw_dsn = os.getenv("SENTRY_DSN", "")
        masked_dsn = f"{raw_dsn[:16]}...{raw_dsn[-8:]}" if len(raw_dsn) > 24 else "***"
        is_connected = True

    environment = getattr(
        logger, "environment", os.getenv("SENTRY_ENVIRONMENT", "development")
    )
    release = getattr(
        logger, "release", os.getenv("SENTRY_RELEASE", "hexastack@v0.8.0")
    )

    with ui.row().classes("w-full gap-4 flex-wrap mb-6"):
        with ui.card().classes("hx-card flex-1 min-w-[280px] p-4"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Sentry Error Tracking").classes(
                    "text-base font-bold text-slate-900 dark:text-white"
                )
                if is_connected:
                    ui.chip(
                        "Connected",
                        icon="check_circle",
                        color="green-9",
                        text_color="white",
                    )
                else:
                    ui.chip(
                        "Not Configured",
                        icon="error_outline",
                        color="amber-9",
                        text_color="white",
                    )

            ui.label(f"Active Environment: {environment}").classes(
                "text-sm text-slate-700 dark:text-slate-300"
            )
            ui.label(f"Release Tag: {release}").classes(
                "text-sm text-slate-700 dark:text-slate-300"
            )
            ui.label(f"DSN: {masked_dsn or 'None (set SENTRY_DSN in .env)'}").classes(
                "text-xs text-slate-500 font-mono mt-2"
            )

        with ui.card().classes("hx-card flex-1 min-w-[280px] p-4"):
            ui.label("Active Logging Engine").classes(
                "text-base font-bold text-slate-900 dark:text-white mb-2"
            )
            logger_name = type(logger).__name__ if logger else "Not Bound"
            ui.label(f"Adapter: {logger_name}").classes(
                "text-sm text-slate-700 dark:text-slate-300"
            )
            inner = getattr(logger, "_inner", None)
            if inner:
                ui.label(f"Wrapped Logger: {type(inner).__name__}").classes(
                    "text-sm text-slate-500"
                )


def _build_mermaid_middlewares(container: Container, lines: list[str]) -> None:
    """Append middleware chain nodes and links to Mermaid lines."""
    from hexastack_cqrs.ports.buses import CommandBusPort

    cmd_bus = container.resolve(CommandBusPort) if CommandBusPort in container else None
    middlewares = getattr(cmd_bus, "_middleware", []) if cmd_bus else []
    if not middlewares:
        lines.append('    Client --> Pipeline["Execution Pipeline"]')
        return

    mw_nodes: list[str] = []
    for idx, mw in enumerate(middlewares, 1):
        mw_name = type(mw).__name__
        mw_id = f"MW{idx}"
        lines.append(f'    {mw_id}["{idx}. {mw_name}"]')
        mw_nodes.append(mw_id)

    lines.append(f"    Client --> {mw_nodes[0]}")
    for i in range(len(mw_nodes) - 1):
        lines.append(f"    {mw_nodes[i]} --> {mw_nodes[i + 1]}")
    lines.append(f'    {mw_nodes[-1]} --> Pipeline["Execution Pipeline"]')


def _build_mermaid_cqrs(
    container: Container, lines: list[str]
) -> tuple[bool, list[str], list[str]]:
    """Append CQRS message nodes and links to Mermaid lines.

    Returns:
        Tuple of (has_cqrs, cmd_names, qry_names).
    """
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry

    cmd_reg = (
        container.resolve(CommandRegistry) if CommandRegistry in container else None
    )
    qry_reg = container.resolve(QueryRegistry) if QueryRegistry in container else None

    cmd_names = (
        [getattr(k, "__name__", str(k)) for k in cmd_reg.all.values()]
        if cmd_reg
        else []
    )
    qry_names = (
        [getattr(k, "__name__", str(k)) for k in qry_reg.all.values()]
        if qry_reg
        else []
    )

    has_cqrs = False
    if cmd_names:
        has_cqrs = True
        cmd_label = (
            f"Commands ({', '.join(cmd_names)})"
            if len(cmd_names) <= 3
            else f"Commands ({len(cmd_names)} registered)"
        )
        lines.append(f'    Pipeline --> Commands["{cmd_label}"]')

    if qry_names:
        has_cqrs = True
        qry_label = (
            f"Queries ({', '.join(qry_names)})"
            if len(qry_names) <= 3
            else f"Queries ({len(qry_names)} registered)"
        )
        lines.append(f'    Pipeline --> Queries["{qry_label}"]')

    return has_cqrs, cmd_names, qry_names


def _detect_sentry_presence(container: Container, service_names: list[str]) -> bool:
    """Check if Sentry adapter or logging integration is present in container."""
    if any("Sentry" in s for s in service_names):
        return True
    from hexastack_core.ports.logging import LoggingPort

    if LoggingPort in container:
        try:
            resolved_logger = container.resolve(LoggingPort)
            name = type(resolved_logger).__name__
            return "Sentry" in name or bool(
                getattr(resolved_logger, "is_connected", False)
            )
        except Exception:
            return False
    return False


def _append_storage_mermaid(
    lines: list[str], cmd_names: list[str], qry_names: list[str]
) -> None:
    """Append persistence links connecting commands or queries to Storage."""
    lines.append('    Storage["Persistence / Repositories"]')
    if cmd_names:
        lines.append("    Commands --> Storage")
    if qry_names:
        lines.append("    Queries --> Storage")
    if not cmd_names and not qry_names:
        lines.append("    Pipeline --> Storage")


def _build_mermaid_ports(
    container: Container,
    lines: list[str],
    cmd_names: list[str],
    qry_names: list[str],
) -> bool:
    """Append external port nodes and linkages to Mermaid lines.

    Returns:
        True if any external ports were added, False otherwise.
    """
    service_map = getattr(container, "_map", {})
    service_names = [getattr(cls, "__name__", str(cls)) for cls in service_map]

    has_event_bus = any("EventBus" in s for s in service_names)
    has_flags = any("FeatureFlag" in s or "Flag" in s for s in service_names)
    has_storage = any(
        "Repository" in s or "UnitOfWork" in s or "Database" in s for s in service_names
    )
    has_cache = any("Cache" in s or "Lock" in s for s in service_names)
    has_sentry = _detect_sentry_presence(container, service_names)

    if has_flags:
        lines.append('    Pipeline -.-> Flags["Feature Flag Port"]')

    if has_event_bus:
        lines.append('    EventBus["Distributed Event Bus"]')
        target = "Commands" if cmd_names else "Pipeline"
        lines.append(f"    {target} -.-> EventBus")

    if has_storage:
        _append_storage_mermaid(lines, cmd_names, qry_names)

    if has_cache:
        lines.append('    Pipeline -.-> Cache["Cache & Lock Ports"]')

    if has_sentry:
        lines.append('    Pipeline -.-> Sentry["Sentry Error Reporting"]')

    return bool(has_event_bus or has_flags or has_storage or has_cache or has_sentry)


def generate_topology_mermaid(
    container: Container,
    pipeline: ExecutionPipeline | None = None,
) -> str:
    """Generate a Mermaid diagram representing runtime resource interconnects.

    Inspects registered CQRS messages, middleware chains, event buses,
    repositories, and feature flag adapters in the DI container.

    Args:
        container: Application dependency injection container.
        pipeline: Optional CQRS execution pipeline instance.

    Returns:
        Mermaid syntax string (graph LR).

    Raises:
        None.

    Notes/Architectural Intent:
        Constructs an architectural topology graph for real-time visualization
        in Hexastack DevTools, exposing data flow relationships between
        entrypoint clients, middlewares, command/query dispatchers, and external ports.
    """
    lines = ["graph LR", '    Client["Client / Entrypoint"]']
    _build_mermaid_middlewares(container, lines)
    has_cqrs, cmd_names, qry_names = _build_mermaid_cqrs(container, lines)
    has_ports = _build_mermaid_ports(container, lines, cmd_names, qry_names)

    if not has_cqrs and not has_ports:
        lines.append(
            '    Pipeline --> EmptyServices["DI Container (No services registered)"]'
        )

    return "\n".join(lines)


def _render_topology_tab(
    container: Container, pipeline: ExecutionPipeline | None = None
) -> None:
    """Render resource interconnect topology graph tab using Mermaid."""
    from nicegui import ui

    ui.label("Resource Interconnect Topology").classes("hx-section-heading")
    ui.label(
        "Interactive architectural interconnect graph across entrypoints, "
        "CQRS pipelines, event buses, and storage ports."
    ).classes("hx-subtext")

    mermaid_code = generate_topology_mermaid(container, pipeline)
    with ui.card().classes("hx-card w-full items-center justify-center p-4"):
        ui.mermaid(mermaid_code).classes("w-full")


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
        tab_observability = ui.tab("Observability", icon="monitor_heart")
        tab_topology = ui.tab("Resource Topology", icon="account_tree")

    with ui.tab_panels(tabs, value=tab_cqrs).classes("w-full p-6"):
        with ui.tab_panel(tab_cqrs):
            _render_cqrs_tab(container, pipeline=pipeline)

        with ui.tab_panel(tab_flags):
            _render_flags_tab(container)

        with ui.tab_panel(tab_container):
            _render_container_tab(container)

        with ui.tab_panel(tab_observability):
            _render_observability_tab(container)

        with ui.tab_panel(tab_topology):
            _render_topology_tab(container, pipeline=pipeline)


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

    static_dir = _resolve_static_dir()
    if static_dir and static_dir.is_dir():
        nicegui_app.add_static_files("/_hexastack/ui/static", str(static_dir))

    mount_ui_app(app, title=title)

    @ui.page(path, title=title)
    def devtools_page():
        _render_devtools_content(container, pipeline, title)
