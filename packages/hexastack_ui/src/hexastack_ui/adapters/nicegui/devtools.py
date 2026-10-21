"""Turnkey DevTools diagnostic dashboard built on NiceGUI.

Notes/Architectural Intent:
    Renders an interactive inspector for CQRS registries, command bus middlewares,
    feature flag state, and DI container service bindings.
"""

from __future__ import annotations

import asyncio
import importlib.resources
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rodi import Container

from hexastack_core.utils.imports import optional_dependency
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort
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


def _resolve_pipeline_from_container(
    container: Container,
) -> ExecutionPipelinePort | None:
    """Resolve an ExecutionPipelinePort from a DI container, checking port and subclasses.

    Args:
        container: Dependency injection container to inspect.

    Returns:
        ExecutionPipelinePort instance if registered or resolvable, else None.

    Raises:
        None.

    Notes/Architectural Intent:
        Inspects declared port first, followed by introspecting registered types in
        the container to support concrete subclasses without hardcoded infra imports.
    """
    if ExecutionPipelinePort in container:
        return container.resolve(ExecutionPipelinePort)
    for cls in getattr(container, "_map", {}):
        if isinstance(cls, type) and issubclass(cls, ExecutionPipelinePort):
            return container.resolve(cls)
    return None


def _extract_cqrs_from_pipeline(
    pipeline: ExecutionPipelinePort,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract registered commands and queries from an ExecutionPipelinePort."""
    cmds: dict[str, Any] = {}
    qrys: dict[str, Any] = {}
    try:
        res_cmds = pipeline.get_registered_commands()
        if isinstance(res_cmds, dict):
            cmds = res_cmds
    except Exception:
        pass
    try:
        res_qrys = pipeline.get_registered_queries()
        if isinstance(res_qrys, dict):
            qrys = res_qrys
    except Exception:
        pass
    return cmds, qrys


def _extract_cqrs_from_container(
    container: Container,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract registered commands and queries by introspecting container registries."""
    cmds: dict[str, Any] = {}
    qrys: dict[str, Any] = {}
    for reg_cls in getattr(container, "_map", {}):
        cls_name = getattr(reg_cls, "__name__", "")
        if cls_name == "CommandRegistry" and reg_cls in container:
            try:
                creg = container.resolve(reg_cls)
                cmds = getattr(creg, "all", {})
            except Exception:
                pass
        elif cls_name == "QueryRegistry" and reg_cls in container:
            try:
                qreg = container.resolve(reg_cls)
                qrys = getattr(qreg, "all", {})
            except Exception:
                pass
    return cmds, qrys


def _extract_registered_cqrs(
    container: Container,
    pipeline: ExecutionPipelinePort | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract registered commands and queries from pipeline or container fallback.

    Args:
        container: Dependency injection container.
        pipeline: Optional ExecutionPipelinePort instance.

    Returns:
        Tuple of (commands_dict, queries_dict).

    Raises:
        None.

    Notes/Architectural Intent:
        Queries ExecutionPipelinePort first for registered message schemas. If absent,
        falls back to inspecting CommandRegistry and QueryRegistry in the container
        without directly importing concrete infra classes.
    """
    pipe = pipeline or _resolve_pipeline_from_container(container)
    if pipe is not None:
        cmds, qrys = _extract_cqrs_from_pipeline(pipe)
        if cmds or qrys:
            return cmds, qrys
    return _extract_cqrs_from_container(container)


def _find_ping_command(
    container: Container,
    pipeline: ExecutionPipelinePort | None,
) -> type[Any] | None:
    """Find a registered Command type with 'ping' in its name.

    Args:
        container: Dependency injection container.
        pipeline: ExecutionPipelinePort instance if available.

    Returns:
        Command class if found, otherwise None.

    Raises:
        None.

    Notes/Architectural Intent:
        Supports dynamic DevTools ping command discovery across varying application models.
    """
    cmds, _ = _extract_registered_cqrs(container, pipeline)
    for name, cls in cmds.items():
        if "ping" in str(name).lower():
            return cls
    return None


def _render_cqrs_messages(container: Container) -> None:
    """Render table of registered CQRS message contracts."""
    from nicegui import ui

    ui.label("Registered CQRS Commands & Queries").classes("hx-section-heading")

    cmds, qrys = _extract_registered_cqrs(container)
    commands_list = [
        {"type": "Command", "name": getattr(k, "__name__", str(k))}
        for k in cmds.values()
    ]
    queries_list = [
        {"type": "Query", "name": getattr(k, "__name__", str(k))} for k in qrys.values()
    ]

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
    pipeline: ExecutionPipelinePort | None,
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
        active_pipeline = pipeline or _resolve_pipeline_from_container(container)
        if active_pipeline is not None:
            cmd_cls = _find_ping_command(container, active_pipeline)
            if cmd_cls is not None:
                cmd_instance = cmd_cls.model_validate({"message": ping_value})
                res = active_pipeline.execute(cmd_instance)
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
    pipeline: ExecutionPipelinePort | None,
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
    container: Container, pipeline: ExecutionPipelinePort | None = None
) -> None:
    """Render the CQRS tab panel showing registered messages, middleware pipeline, and live runner."""
    from hexastack_cqrs.ports.buses import CommandBusPort

    _render_cqrs_messages(container)
    cmd_bus = container.resolve(CommandBusPort) if CommandBusPort in container else None
    middlewares = getattr(cmd_bus, "_middleware", []) if cmd_bus else []
    _render_middleware_chain(middlewares)
    _render_live_runner(container, pipeline, middlewares)


def _render_flag_row(
    flag_key: str,
    flag_val: Any,
    set_flag_fn: Any,
    log_output: Any,
) -> None:
    """Render a single feature flag row with hot-swapping switch or badge."""
    from nicegui import ui

    with ui.row().classes(
        "w-full items-center justify-between py-2 border-b border-slate-200 dark:border-slate-700"
    ):
        with ui.column().classes("gap-1"):
            ui.label(flag_key).classes(
                "font-mono font-medium text-slate-900 dark:text-slate-100"
            )
            type_name = type(flag_val).__name__
            ui.label(f"Type: {type_name}").classes(
                "text-xs text-slate-600 dark:text-slate-400"
            )

        if isinstance(flag_val, bool):

            def _on_change(e: Any) -> None:
                new_val = bool(e.value)
                if callable(set_flag_fn):
                    set_flag_fn(flag_key, new_val)
                    log_output.push(
                        f"🔄 [HOT-SWAP] Feature flag '{flag_key}' toggled to {new_val}"
                    )
                    ui.notify(
                        f"Flag '{flag_key}' set to {new_val}",
                        color="green-10",
                    )

            ui.switch(
                text="Enabled" if flag_val else "Disabled",
                value=flag_val,
                on_change=_on_change,
            ).classes("text-sm").props(f'aria-label="Toggle {flag_key}"')
        else:
            ui.badge(str(flag_val), color="blue-grey").classes("font-mono text-sm")


def _render_flags_tab(container: Container) -> None:
    """Render the feature flags tab panel showing active flags and hot-swap controls."""
    from nicegui import ui

    from hexastack_core.ports.feature_flags import FeatureFlagPort

    ui.label("Active Feature Flags").classes("hx-section-heading")
    ui.label(
        "Evaluate and hot-swap feature flags live without requiring application restarts."
    ).classes("hx-subtext")

    flags_adapter = (
        container.resolve(FeatureFlagPort) if FeatureFlagPort in container else None
    )

    get_all_fn = getattr(flags_adapter, "get_all_flags", None)
    set_flag_fn = getattr(flags_adapter, "set_flag", None)

    if callable(get_all_fn):
        flags_data: dict[str, Any] = get_all_fn()
        if flags_data:
            with ui.card().classes("hx-card w-full p-4"):
                log_output = ui.log(max_lines=10).classes("hx-log-console mb-4")
                for k, v in flags_data.items():
                    _render_flag_row(k, v, set_flag_fn, log_output)
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
        logger, "release", os.getenv("SENTRY_RELEASE", "hexastack@v0.9.0")
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
                        color="grey-9",
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

    Args:
        container: Dependency injection container.
        lines: Output list of Mermaid lines.

    Returns:
        Tuple of (has_cqrs, cmd_names, qry_names).

    Raises:
        None.

    Notes/Architectural Intent:
        Renders Mermaid CQRS subgraphs for commands and queries discovered via pipeline or container.
    """
    cmds, qrys = _extract_registered_cqrs(container)
    cmd_names = [getattr(k, "__name__", str(k)) for k in cmds.values()]
    qry_names = [getattr(k, "__name__", str(k)) for k in qrys.values()]

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
    pipeline: ExecutionPipelinePort | None = None,
) -> str:
    """Generate a Mermaid diagram representing runtime resource interconnects.

    Inspects registered CQRS messages, middleware chains, event buses,
    repositories, and feature flag adapters in the DI container.

    Args:
        container: Application dependency injection container.
        pipeline: Optional CQRS execution pipeline port instance.

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
    container: Container, pipeline: ExecutionPipelinePort | None = None
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


def _build_demo_workflow(hexaflow_mod: Any) -> Any:
    """Build a representative multi-stage order saga for DevTools visualization.

    Args:
        hexaflow_mod: Imported hexaflow module or namespace.

    Returns:
        Workflow instance configured with stages and steps.
    """
    wf = hexaflow_mod.Workflow(name="order_saga", version="1.0.0")

    @wf.stage("validation")
    @wf.step("validate_order")
    def validate_order(ctx: Any) -> dict[str, Any]:
        return {"order_id": "ord-101", "valid": True}

    @wf.stage("payment")
    @wf.step(
        "authorize_payment",
        depends_on=["validate_order"],
        side_effects=True,
        dry_run=lambda: {"status": "AUTH_SIMULATED"},
    )
    def authorize_payment(ctx: Any) -> dict[str, Any]:
        return {"status": "PAID"}

    @wf.stage("fulfillment")
    @wf.step(
        "dispatch_order",
        depends_on=["authorize_payment"],
        side_effects=True,
        dry_run=lambda: {"tracking": "SIM-TRACK-999"},
    )
    def dispatch_order(ctx: Any) -> dict[str, Any]:
        return {"tracking": "TRK-001"}

    return wf


def _resolve_available_workflows(
    container: Container,
    orchestrator: Any,
    hexaflow_mod: Any,
) -> dict[str, Any]:
    """Discover registered application workflows, providing a demo saga as fallback.

    Args:
        container: Application DI container.
        orchestrator: Optional workflow orchestrator port implementation.
        hexaflow_mod: Imported hexaflow module or namespace.

    Returns:
        Mapping of workflow display names to workflow definitions or instances.
    """
    workflows: dict[str, Any] = {}
    props = getattr(container, "properties", {})
    if isinstance(props, dict):
        reg = props.get("workflows")
        if isinstance(reg, dict):
            workflows.update(reg)
    if (
        orchestrator
        and hasattr(orchestrator, "workflows")
        and isinstance(orchestrator.workflows, dict)
    ):
        workflows.update(orchestrator.workflows)

    demo = _build_demo_workflow(hexaflow_mod)
    demo_key = "order_saga (Demo)"
    if demo_key not in workflows:
        workflows[demo_key] = demo
    return workflows


def _resolve_orchestrator(container: Container) -> Any | None:
    """Resolve workflow orchestrator port from DI container if registered.

    Args:
        container: Application DI container.

    Returns:
        Resolved orchestrator instance or None.
    """
    service_map = getattr(container, "_map", {})
    for cls in service_map:
        if getattr(cls, "__name__", "") == "CqrsWorkflowOrchestratorPort":
            try:
                return container.resolve(cls)
            except Exception:
                return None
    return None


def _render_workflow_mermaid(
    orchestrator: Any,
    workflow: Any,
    direction: Any = "TD",
    highlight_cp: bool = False,
    highlight_nodes: set[str] | None = None,
) -> str:
    """Render workflow DAG to Mermaid string with direction and highlighting options.

    Args:
        orchestrator: Optional orchestrator port.
        workflow: Target workflow definition or instance.
        direction: Layout direction ('TD' or 'LR').
        highlight_cp: Whether to highlight critical execution path.
        highlight_nodes: Optional set of step IDs to visually highlight.

    Returns:
        Mermaid diagram source code string.
    """
    if workflow is None:
        return "graph TD\n  empty[No workflow diagram available]"

    opts = None
    try:
        from hexaflow.ports.renderer import RenderOptions

        opts = RenderOptions(
            direction=direction,
            highlight_critical_path=highlight_cp,
            highlight_node_ids=frozenset(highlight_nodes)
            if highlight_nodes
            else frozenset(),
        )
    except Exception:
        opts = None

    try:
        if orchestrator and hasattr(orchestrator, "render"):
            return str(
                orchestrator.render(workflow, format_name="mermaid", options=opts)
            )
        if opts and hasattr(workflow, "render"):
            return str(workflow.render("mermaid", options=opts))
        if hasattr(workflow, "render"):
            return str(workflow.render("mermaid"))
    except Exception:
        if hasattr(workflow, "render"):
            return str(workflow.render("mermaid"))
    return "graph TD\n  empty[No workflow diagram available]"


def _run_sync_safe(target_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute callable safely, offloading to a worker thread if an event loop is running.

    Args:
        target_fn: Function to invoke.
        *args: Positional arguments for target_fn.
        **kwargs: Keyword arguments for target_fn.

    Returns:
        Result returned by target_fn.
    """
    try:
        asyncio.get_running_loop()
        is_loop = True
    except RuntimeError:
        is_loop = False

    if is_loop:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(target_fn, *args, **kwargs).result()
    return target_fn(*args, **kwargs)


def _invoke_simulation(orchestrator: Any, workflow: Any) -> tuple[str, list[str], Any]:
    """Invoke simulation on orchestrator or workflow object safely.

    Args:
        orchestrator: Optional orchestrator port.
        workflow: Target workflow definition or instance.

    Returns:
        Tuple of (status_val, completed_steps, outputs).

    Raises:
        TypeError: If workflow cannot be simulated.
    """
    if orchestrator and hasattr(orchestrator, "simulate"):
        res = _run_sync_safe(orchestrator.simulate, workflow)
        return str(res.status), list(res.completed_steps), res.outputs
    if hasattr(workflow, "simulate"):
        state = _run_sync_safe(workflow.simulate)
        outputs = {k: v.output_payload for k, v in state.step_checkpoints.items()}
        return str(state.status.value), list(state.step_checkpoints.keys()), outputs
    raise TypeError("Workflow cannot be simulated.")


def _execute_saga_simulation(
    orchestrator: Any,
    workflow: Any,
    log_output: Any,
) -> list[str]:
    """Execute dry-run simulation and log step progress.

    Args:
        orchestrator: Optional orchestrator port.
        workflow: Target workflow to simulate.
        log_output: NiceGUI log component to output traces.

    Returns:
        List of completed step names.
    """
    if workflow is None:
        log_output.push("❌ [ERROR] No workflow selected for simulation.")
        return []

    wf_label = getattr(workflow, "name", "workflow")
    log_output.push(
        f"▶️ [SIMULATION] Starting dry-run saga simulation for '{wf_label}'..."
    )
    try:
        status_val, completed, outputs = _invoke_simulation(orchestrator, workflow)
        log_output.push(f"   ↳ [STATUS] {status_val}")
        log_output.push(f"   ↳ [COMPLETED STEPS] {', '.join(completed)}")
        log_output.push(f"   ↳ [SIMULATED OUTPUTS] {outputs}")

        if status_val == "COMPLETED":
            log_output.push(
                "✅ [SUCCESS] Dry-run simulation completed safely with 0 side effects."
            )
        else:
            log_output.push(
                f"⚠️ [WARNING] Dry-run simulation ended with status: {status_val}"
            )
        return completed
    except Exception as exc:
        log_output.push(f"❌ [ERROR] Simulation failed: {exc}")
        return []


def _render_workflow_tab(container: Container) -> None:
    """Render interactive workflow DAG visualizer and saga simulation panel.

    Args:
        container: Application DI container providing services and orchestrator.
    """
    from nicegui import ui

    ui.label("Workflow Orchestration & DAG Visualizer").classes("hx-section-heading")
    ui.label(
        "Interactive workflow DAG rendering and dry-run saga simulation powered by hexaflow."
    ).classes("hx-subtext")

    orchestrator = _resolve_orchestrator(container)
    hexaflow = optional_dependency("hexaflow")
    if hexaflow is None:
        with ui.card().classes("hx-card w-full p-4"):
            ui.label(
                "Workflow tools require the optional 'hexaflow' dependency."
            ).classes("text-slate-500 italic")
        return

    workflows = _resolve_available_workflows(container, orchestrator, hexaflow)
    wf_names = list(workflows.keys())
    active_wf_name = [wf_names[0]]
    highlighted_steps: set[str] = set()

    with ui.card().classes("hx-card w-full mb-6 p-4"):
        with ui.row().classes(
            "w-full items-center justify-between mb-3 flex-wrap gap-2"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("account_tree", size="sm").classes("text-blue-500")
                ui.label("Workflow Execution Graph (Mermaid)").classes(
                    "font-semibold text-slate-700 dark:text-slate-200"
                )

            with ui.row().classes("items-center gap-3"):
                wf_select = ui.select(
                    options=wf_names,
                    value=active_wf_name[0],
                    label="Active Workflow",
                ).classes("w-56 text-xs")

                dir_select = ui.select(
                    {"TD": "Top-to-Bottom (TD)", "LR": "Left-to-Right (LR)"},
                    value="TD",
                    label="Layout Direction",
                ).classes("w-44 text-xs")

                cp_switch = ui.switch("Critical Path", value=False).classes("text-xs")

        initial_mermaid = _render_workflow_mermaid(
            orchestrator,
            workflows.get(active_wf_name[0]),
            direction=str(dir_select.value or "TD"),
            highlight_cp=bool(cp_switch.value),
        )
        mermaid_view = ui.mermaid(initial_mermaid).classes("w-full")

        def _update_view() -> None:
            active_wf_name[0] = wf_select.value or wf_names[0]
            new_code = _render_workflow_mermaid(
                orchestrator,
                workflows.get(active_wf_name[0]),
                direction=str(dir_select.value or "TD"),
                highlight_cp=bool(cp_switch.value),
                highlight_nodes=highlighted_steps,
            )
            mermaid_view.set_content(new_code)

        wf_select.on_value_change(_update_view)
        dir_select.on_value_change(_update_view)
        cp_switch.on_value_change(_update_view)

    with ui.card().classes("hx-card w-full p-4"):
        ui.label("Dry-Run Saga Simulator").classes(
            "font-semibold text-slate-700 dark:text-slate-200 mb-2"
        )
        ui.label(
            "Simulate workflow execution with side-effect fail-closed guards without mutating production databases:"
        ).classes("hx-subtext")

        log_output = ui.log(max_lines=12).classes("hx-log-console mb-3")

        def _run_sim() -> None:
            completed = _execute_saga_simulation(
                orchestrator,
                workflows.get(active_wf_name[0]),
                log_output,
            )
            highlighted_steps.clear()
            highlighted_steps.update(completed)
            _update_view()

        def _reset_sim() -> None:
            highlighted_steps.clear()
            _update_view()
            log_output.push("🔄 [RESET] Visual highlights cleared.")

        with ui.row().classes("gap-2 mt-2"):
            ui.button(
                "Simulate Saga", on_click=_run_sim, icon="play_arrow", color="blue-9"
            ).classes("text-white font-medium shadow-sm").tooltip(
                "Execute dry-run simulation safely"
            )
            ui.button(
                "Reset Highlights",
                on_click=_reset_sim,
                icon="restart_alt",
                color="grey-8",
            ).classes("text-white font-medium shadow-sm").tooltip(
                "Reset graph step highlights"
            )


def _render_devtools_content(
    container: Container,
    pipeline: ExecutionPipelinePort | None,
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
        tab_workflows = ui.tab("Workflows", icon="account_tree")
        tab_flags = ui.tab("Feature Flags", icon="toggle_on")
        tab_container = ui.tab("DI Container", icon="hub")
        tab_observability = ui.tab("Observability", icon="monitor_heart")
        tab_topology = ui.tab("Resource Topology", icon="schema")

    with ui.tab_panels(tabs, value=tab_cqrs).classes("w-full p-6"):
        with ui.tab_panel(tab_cqrs):
            _render_cqrs_tab(container, pipeline=pipeline)

        with ui.tab_panel(tab_workflows):
            _render_workflow_tab(container)

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
    pipeline: ExecutionPipelinePort | None = None,
    *,
    path: str = "/_devtools",
    title: str = "Hexastack DevTools",
) -> None:
    """Mount the default Hexastack interactive DevTools dashboard on FastAPI.

    Args:
        app: Target FastAPI application.
        container: Application rodi.Container instance.
        pipeline: Optional ExecutionPipelinePort instance.
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
