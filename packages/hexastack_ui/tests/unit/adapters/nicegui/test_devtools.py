"""Unit tests for NiceGUI DevTools dashboard."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import hexaflow
import pytest
from fastapi import FastAPI
from nicegui import Client, core, ui
from nicegui.page import page
from rodi import Container
from starlette.routing import Mount

from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.domain import Command, Query
from hexastack_core.domain.command import Command as BaseCmd
from hexastack_core.domain.query import Query as BaseQry
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort
from hexastack_flow.domain.models import WorkflowExecutionResult
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort
from hexastack_ui.adapters.nicegui.devtools import (
    _build_demo_workflow,
    _build_mermaid_cqrs,
    _detect_sentry_presence,
    _dispatch_ping,
    _execute_saga_simulation,
    _render_container_tab,
    _render_cqrs_messages,
    _render_cqrs_tab,
    _render_devtools_content,
    _render_flags_tab,
    _render_live_runner,
    _render_middleware_chain,
    _render_observability_tab,
    _render_topology_tab,
    _render_workflow_mermaid,
    _render_workflow_tab,
    _resolve_available_workflows,
    _resolve_static_dir,
    _run_sync_safe,
    generate_topology_mermaid,
    mount_devtools_dashboard,
)


def test_mount_devtools_dashboard():
    """Verify mount_devtools_dashboard attaches to FastAPI app and page renders."""
    app = FastAPI()
    container = Container()
    pipeline = MagicMock(spec=ExecutionPipelinePort)

    mount_devtools_dashboard(
        app, container=container, pipeline=pipeline, path="/_devtools"
    )

    assert any(isinstance(r, Mount) for r in app.routes)
    assert len(core.app.routes) > 0


def test_render_internal_tabs():
    """Verify internal rendering helpers execute cleanly across container states."""
    client = Client(page("/test-render-tabs"))
    with client.layout.default_slot:
        empty_container = Container()
        _render_cqrs_messages(empty_container)
        _render_middleware_chain([])
        _render_live_runner(empty_container, None, [])
        _render_cqrs_tab(empty_container, None)
        _render_workflow_tab(empty_container)
        _render_flags_tab(empty_container)
        _render_container_tab(empty_container)
        _render_topology_tab(empty_container, None)

        container = Container()
        cmd_reg = CommandRegistry()
        qry_reg = QueryRegistry()

        class PlainCmd(BaseCmd):
            pass

        class PlainQry(BaseQry):
            pass

        cmd_reg.register(PlainCmd)
        qry_reg.register(PlainQry)

        container.add_instance(cmd_reg, declared_class=CommandRegistry)
        container.add_instance(qry_reg, declared_class=QueryRegistry)

        flags_adapter = InMemoryFeatureFlagAdapter({"beta_feature": True, "limit": 100})
        container.add_instance(flags_adapter, declared_class=FeatureFlagPort)

        cmd_bus_mock = MagicMock()
        mw = CorrelationMiddleware()
        cmd_bus_mock._middleware = [mw]
        container.add_instance(cmd_bus_mock, declared_class=CommandBusPort)

        pipeline_mock = MagicMock(spec=ExecutionPipelinePort)
        pipeline_mock.execute = MagicMock(return_value="executed-ok")

        class AuthTestMiddleware:
            pass

        _render_cqrs_messages(container)
        _render_middleware_chain([mw, AuthTestMiddleware()])
        _render_live_runner(container, pipeline_mock, [mw])
        _render_cqrs_tab(container, pipeline=pipeline_mock)
        _render_workflow_tab(container)
        _render_flags_tab(container)
        _render_container_tab(container)
        _render_topology_tab(container, pipeline=pipeline_mock)


def _find_button_and_click(element):
    """Helper to find button with text 'Dispatch Ping Command' recursively."""
    if getattr(element, "text", "") == "Dispatch Ping Command":
        return element._props.get("on_click")
    slot = getattr(element, "default_slot", None)
    children = getattr(slot, "children", []) if slot is not None else []
    for child in children:
        handler = _find_button_and_click(child)
        if handler:
            return handler
    return None


@pytest.mark.anyio
async def test_dispatch_ping_direct():
    """Verify _dispatch_ping handles all resolution branches and log formats."""
    log_output = MagicMock()

    # 1. Pipeline + Registered Ping command
    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingDemoCommand(Command):
        message: str = ""

    creg.register(PingDemoCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline = MagicMock(spec=ExecutionPipelinePort)
    pipeline.execute = MagicMock(return_value="PONG: Direct")
    container.add_instance(pipeline, declared_class=ExecutionPipelinePort)

    class AuthTraceMiddleware:
        pass

    await _dispatch_ping("hello", container, None, [AuthTraceMiddleware()], log_output)
    pipeline.execute.assert_called_once()
    assert (
        log_output.push.call_args_list[0][0][0]
        == "➡️ [DISPATCH] PingDemoCommand(message='hello')"
    )
    assert (
        log_output.push.call_args_list[1][0][0]
        == "   ↳ [MIDDLEWARE] Intercepting through AuthTraceMiddleware..."
    )
    assert (
        log_output.push.call_args_list[2][0][0] == "✅ [SUCCESS] Result: PONG: Direct"
    )

    # 2. Pipeline directly passed, no registered command -> execute_by_name
    log_output.reset_mock()
    pipeline_direct = MagicMock(spec=ExecutionPipelinePort)
    pipeline_direct.execute_by_name = MagicMock(return_value="PONG: DirectName")
    await _dispatch_ping("hello", Container(), pipeline_direct, [], log_output)
    pipeline_direct.execute_by_name.assert_called_once_with(
        "PingDemoCommand", {"message": "hello"}
    )
    assert (
        log_output.push.call_args_list[0][0][0]
        == "➡️ [DISPATCH] PingDemoCommand(message='hello')"
    )
    assert (
        log_output.push.call_args_list[1][0][0]
        == "✅ [SUCCESS] Result: PONG: DirectName"
    )

    # 3. No pipeline -> warning
    log_output.reset_mock()
    await _dispatch_ping("hello", Container(), None, [], log_output)
    assert (
        log_output.push.call_args_list[1][0][0]
        == "⚠️ [WARNING] ExecutionPipeline instance not directly bound."
    )

    # 4. Error handling -> error log
    log_output.reset_mock()
    pipeline_err = MagicMock(spec=ExecutionPipelinePort)
    pipeline_err.execute_by_name.side_effect = RuntimeError("DB connection dropped")
    await _dispatch_ping("fail", Container(), pipeline_err, [], log_output)
    assert (
        "❌ [ERROR] Execution failed: DB connection dropped"
        in log_output.push.call_args_list[-1][0][0]
    )


def test_render_middleware_chain_elements(monkeypatch):
    """Verify middleware chain chips, icons, and handler badge."""
    captured_chips: list[dict] = []
    orig_chip = ui.chip

    def mock_chip(text, *args, **kwargs):
        captured_chips.append({"text": text, **kwargs})
        return orig_chip(text, *args, **kwargs)

    monkeypatch.setattr(ui, "chip", mock_chip)

    class AuthBearerMiddleware:
        pass

    class TimingMiddleware:
        pass

    client = Client(page("/test-mw-chain"))
    with client.layout.default_slot:
        # Empty chain
        _render_middleware_chain([])

        # Active chain with Auth and Timing
        _render_middleware_chain([AuthBearerMiddleware(), TimingMiddleware()])
        assert len(captured_chips) == 3
        assert captured_chips[0]["text"] == "1. AuthBearerMiddleware"
        assert captured_chips[0]["icon"] == "security"
        assert captured_chips[0]["color"] == "blue-9"
        assert captured_chips[0]["text_color"] == "white"

        assert captured_chips[1]["text"] == "2. TimingMiddleware"
        assert captured_chips[1]["icon"] == "filter_alt"

        assert captured_chips[2]["text"] == "Handler Execution"
        assert captured_chips[2]["icon"] == "play_circle"
        assert captured_chips[2]["color"] == "green-9"
        assert captured_chips[2]["text_color"] == "white"


def test_render_devtools_content():
    """Verify _render_devtools_content builds all tabs and header."""
    container = Container()
    pipeline = MagicMock(spec=ExecutionPipelinePort)

    client = Client(page("/test-devtools-full"))
    with client.content:
        _render_devtools_content(container, pipeline, "Hexastack DevTools Full Test")


def test_render_table_structures_and_schemas(monkeypatch):
    """Verify table structures, column definitions, and row formatting across tabs."""
    captured_tables: list[dict] = []
    orig_table = ui.table

    def mock_table(*args, **kwargs):
        captured_tables.append(kwargs)
        return orig_table(*args, **kwargs)

    monkeypatch.setattr(ui, "table", mock_table)

    captured_switches: list[dict] = []
    orig_switch = ui.switch

    def mock_switch(*args, **kwargs):
        captured_switches.append(kwargs)
        return orig_switch(*args, **kwargs)

    monkeypatch.setattr(ui, "switch", mock_switch)

    captured_badges: list[dict] = []
    orig_badge = ui.badge

    def mock_badge(text, *args, **kwargs):
        captured_badges.append({"text": text, **kwargs})
        return orig_badge(text, *args, **kwargs)

    monkeypatch.setattr(ui, "badge", mock_badge)

    client = Client(page("/test-table-schemas"))
    with client.layout.default_slot:
        container = Container()

        # 1. CQRS messages table
        cmd_reg = CommandRegistry()
        qry_reg = QueryRegistry()

        class AlphaCommand(BaseCmd):
            pass

        class BetaQuery(BaseQry):
            pass

        cmd_reg.register(AlphaCommand)
        qry_reg.register(BetaQuery)
        container.add_instance(cmd_reg, declared_class=CommandRegistry)
        container.add_instance(qry_reg, declared_class=QueryRegistry)

        _render_cqrs_messages(container)
        cqrs_table = captured_tables[-1]
        assert len(cqrs_table["columns"]) == 2
        assert cqrs_table["columns"][0] == {
            "name": "type",
            "label": "Message Type",
            "field": "type",
            "sortable": True,
        }
        assert cqrs_table["columns"][1] == {
            "name": "name",
            "label": "Class Name",
            "field": "name",
            "sortable": True,
        }
        assert cqrs_table["row_key"] == "name"
        assert cqrs_table["rows"] == [
            {"type": "Command", "name": "AlphaCommand"},
            {"type": "Query", "name": "BetaQuery"},
        ]

        # 2. Feature flags controls (interactive switches & badges)
        flags_adapter = InMemoryFeatureFlagAdapter({"feature_x": True, "quota": 42})
        container.add_instance(flags_adapter, declared_class=FeatureFlagPort)

        _render_flags_tab(container)
        switches_count = len(captured_switches)
        assert switches_count == 1
        assert captured_switches[0]["value"] is True
        assert captured_switches[0]["text"] == "Enabled"

        # Verify hot-swapping switch toggle
        on_change = captured_switches[0]["on_change"]
        change_event = MagicMock()
        change_event.value = False
        on_change(change_event)
        flag_val = flags_adapter.is_enabled("feature_x")
        assert flag_val is False

        # Verify non-boolean badge
        badges_count = len(captured_badges)
        assert badges_count == 1
        assert captured_badges[0]["text"] == "42"

        # 3. DI Container services table
        _render_container_tab(container)
        container_table = captured_tables[-1]
        assert len(container_table["columns"]) == 3
        assert container_table["columns"][0] == {
            "name": "service",
            "label": "Registered Port / Service",
            "field": "service",
            "sortable": True,
        }
        assert container_table["columns"][1] == {
            "name": "module",
            "label": "Module",
            "field": "module",
            "sortable": True,
        }
        assert container_table["columns"][2] == {
            "name": "resolver",
            "label": "Binding / Lifetime",
            "field": "resolver",
            "sortable": True,
        }
        assert container_table["row_key"] == "service"
        assert any(r["service"] == "CommandRegistry" for r in container_table["rows"])

        # 4. Empty container / CQRS messages fallback labels
        captured_labels: list[str] = []
        orig_label = ui.label

        def mock_label(text, *args, **kwargs):
            captured_labels.append(text)
            return orig_label(text, *args, **kwargs)

        monkeypatch.setattr(ui, "label", mock_label)

        empty_container = Container()
        _render_cqrs_messages(empty_container)
        assert "No CQRS messages registered in container." in captured_labels

        _render_container_tab(empty_container)
        assert "No direct services found in container introspection." in captured_labels


@pytest.mark.anyio
async def test_dispatch_ping_validation_error():
    """Verify _dispatch_ping catches validation error and logs error message."""
    log_output = MagicMock()
    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingStrictCommand(Command):
        number: int

    creg.register(PingStrictCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline = MagicMock(spec=ExecutionPipelinePort)
    container.add_instance(pipeline, declared_class=ExecutionPipelinePort)

    # Passing string "not_a_number" causes model_validate to fail for int field
    await _dispatch_ping("not_a_number", container, None, [], log_output)
    pipeline.execute.assert_not_called()
    assert any(
        "❌ [ERROR] Execution failed:" in call[0][0]
        for call in log_output.push.call_args_list
    )


def test_generate_topology_mermaid_empty():
    """Verify generate_topology_mermaid handles empty container cleanly."""
    empty_container = Container()
    mermaid_code = generate_topology_mermaid(empty_container)

    has_graph = "graph LR" in mermaid_code
    assert has_graph is True
    has_client = 'Client["Client / Entrypoint"]' in mermaid_code
    assert has_client is True
    has_pipeline = 'Pipeline["Execution Pipeline"]' in mermaid_code
    assert has_pipeline is True
    has_empty = (
        'Pipeline --> EmptyServices["DI Container (No services registered)"]'
        in mermaid_code
    )
    assert has_empty is True


def test_generate_topology_mermaid_populated():
    """Verify generate_topology_mermaid links middlewares, messages, and ports."""
    container = Container()
    cmd_reg = CommandRegistry()
    qry_reg = QueryRegistry()

    @dataclass(frozen=True)
    class CreateOrderCommand(Command):
        order_id: str

    @dataclass(frozen=True)
    class GetOrderQuery(Query[dict[str, Any]]):
        order_id: str

    cmd_reg.register(CreateOrderCommand)
    qry_reg.register(GetOrderQuery)
    container.add_instance(cmd_reg, declared_class=CommandRegistry)
    container.add_instance(qry_reg, declared_class=QueryRegistry)

    # Middleware chain
    class TraceMiddleware:
        pass

    class MetricsMiddleware:
        pass

    cmd_bus = MagicMock()
    cmd_bus._middleware = [TraceMiddleware(), MetricsMiddleware()]
    container.add_instance(cmd_bus, declared_class=CommandBusPort)

    # Ports
    class FakeEventBusPort:
        pass

    class FakeFeatureFlagPort:
        pass

    class FakeOrderRepository:
        pass

    class FakeCachePort:
        pass

    container.add_instance(FakeEventBusPort(), declared_class=FakeEventBusPort)
    container.add_instance(FakeFeatureFlagPort(), declared_class=FakeFeatureFlagPort)
    container.add_instance(FakeOrderRepository(), declared_class=FakeOrderRepository)
    container.add_instance(FakeCachePort(), declared_class=FakeCachePort)

    mermaid_code = generate_topology_mermaid(container)

    has_mw1 = "MW1" in mermaid_code
    assert has_mw1 is True
    has_mw2 = "MW2" in mermaid_code
    assert has_mw2 is True
    has_cmds = "Commands (CreateOrderCommand)" in mermaid_code
    assert has_cmds is True
    has_qrys = "Queries (GetOrderQuery)" in mermaid_code
    assert has_qrys is True
    has_flags = 'Flags["Feature Flag Port"]' in mermaid_code
    assert has_flags is True
    has_bus = 'EventBus["Distributed Event Bus"]' in mermaid_code
    assert has_bus is True
    has_storage = 'Storage["Persistence / Repositories"]' in mermaid_code
    assert has_storage is True
    has_cache = 'Cache["Cache & Lock Ports"]' in mermaid_code
    assert has_cache is True


def test_generate_topology_mermaid_thresholds():
    """Verify generate_topology_mermaid handles large registries and port fallbacks."""
    container = Container()
    cmd_reg = CommandRegistry()
    qry_reg = QueryRegistry()

    for idx in range(5):
        cmd_type = type(f"Command{idx}", (Command,), {})
        qry_type = type(f"Query{idx}", (Query,), {})
        cmd_reg.register(cmd_type)  # type: ignore[arg-type]
        qry_reg.register(qry_type)  # type: ignore[arg-type]

    container.add_instance(cmd_reg, declared_class=CommandRegistry)
    container.add_instance(qry_reg, declared_class=QueryRegistry)

    mermaid_code = generate_topology_mermaid(container)
    has_cmd_count = "Commands (5 registered)" in mermaid_code
    assert has_cmd_count is True
    has_qry_count = "Queries (5 registered)" in mermaid_code
    assert has_qry_count is True

    # Test container with EventBus and Storage without CQRS
    empty_cqrs_container = Container()

    class FakeEventBusAdapter:
        pass

    class FakeDatabaseUnitOfWork:
        pass

    empty_cqrs_container.add_instance(
        FakeEventBusAdapter(), declared_class=FakeEventBusAdapter
    )
    empty_cqrs_container.add_instance(
        FakeDatabaseUnitOfWork(), declared_class=FakeDatabaseUnitOfWork
    )

    mermaid_code_fallback = generate_topology_mermaid(empty_cqrs_container)
    has_bus_link = "Pipeline -.-> EventBus" in mermaid_code_fallback
    assert has_bus_link is True
    has_storage_link = "Pipeline --> Storage" in mermaid_code_fallback
    assert has_storage_link is True


def test_observability_tab_and_sentry_topology():
    """Verify observability tab renders Sentry health card and topology links Sentry."""
    client = Client(page("/test-render-obs"))
    with client.layout.default_slot:
        empty_c = Container()
        _render_observability_tab(empty_c)

        sentry_c = Container()

        class MockSentryAdapter(LoggingPort):
            is_connected = True
            masked_dsn = "https://dummyk...123456"
            environment = "production"

            release = "hexastack@v0.9.0"

            def debug(self, message: str, extra: Any = None) -> None:
                pass

            def info(self, message: str, extra: Any = None) -> None:
                pass

            def warning(self, message: str, extra: Any = None) -> None:
                pass

            def error(
                self,
                message: str,
                extra: Any = None,
                exc: Exception | None = None,
            ) -> None:
                pass

            def critical(
                self,
                message: str,
                extra: Any = None,
                exc: Exception | None = None,
            ) -> None:
                pass

        mock_sentry = MockSentryAdapter()
        sentry_c.add_instance(mock_sentry, declared_class=LoggingPort)
        _render_observability_tab(sentry_c)

        mermaid_code = generate_topology_mermaid(sentry_c)
        has_sentry_link = (
            'Pipeline -.-> Sentry["Sentry Error Reporting"]' in mermaid_code
        )
        assert has_sentry_link is True


def test_render_workflow_tab_success():
    """Verify _render_workflow_tab renders DAG visualizer and saga simulator."""
    client = Client(page("/test-workflow-tab"))
    with client.layout.default_slot:
        container = Container()
        _render_workflow_tab(container)

    sim_btns = [
        e
        for e in client.elements.values()
        if isinstance(e, ui.button) and e._props.get("label") == "Simulate Saga"
    ]
    assert len(sim_btns) == 1
    listener = list(sim_btns[0]._event_listeners.values())[0]
    handler = listener.handler
    assert callable(handler)
    handler(None)


def test_render_workflow_tab_with_orchestrator():
    """Verify _render_workflow_tab when CqrsWorkflowOrchestratorPort is present."""
    mock_orch = MagicMock(spec=CqrsWorkflowOrchestratorPort)
    mock_orch.render.return_value = "flowchart TD\n  step1-->step2"
    now = datetime.now(UTC)
    mock_orch.simulate.return_value = WorkflowExecutionResult(
        run_id="run-sim-1",
        workflow_name="order_saga",
        status="COMPLETED",
        completed_steps=("validate_order", "authorize_payment", "dispatch_order"),
        outputs={},
        started_at=now,
        ended_at=now,
    )

    container = Container()
    container.add_instance(mock_orch, declared_class=CqrsWorkflowOrchestratorPort)

    client = Client(page("/test-workflow-tab-orch"))
    with client.layout.default_slot:
        _render_workflow_tab(container)

    sim_btns = [
        e
        for e in client.elements.values()
        if isinstance(e, ui.button) and e._props.get("label") == "Simulate Saga"
    ]
    assert len(sim_btns) == 1
    listener = list(sim_btns[0]._event_listeners.values())[0]
    handler = listener.handler
    assert callable(handler)
    handler(None)
    mock_orch.simulate.assert_called_once()


def test_render_workflow_tab_missing_hexaflow(monkeypatch):
    """Verify _render_workflow_tab renders fallback notice when hexaflow is absent."""
    monkeypatch.setattr(
        "hexastack_ui.adapters.nicegui.devtools.optional_dependency",
        lambda name: None,
    )

    client = Client(page("/test-workflow-tab-missing"))
    with client.layout.default_slot:
        container = Container()
        _render_workflow_tab(container)


def test_workflow_visual_controls_and_helpers():
    """Verify workflow DevTools visual controls, direction toggle, and helpers.

    Notes/Architectural Intent:
        Validates layout direction switching, critical path toggling, reset handler,
        and simulation progress tracking without mutating production state.
    """
    demo_wf = _build_demo_workflow(hexaflow)
    name = getattr(demo_wf, "name", "")
    assert name == "order_saga"

    container = Container()
    resolved = _resolve_available_workflows(container, None, hexaflow)
    has_demo = "order_saga (Demo)" in resolved
    assert has_demo is True

    diagram_td = _render_workflow_mermaid(
        None, demo_wf, direction="TD", highlight_cp=False
    )
    is_str_td = isinstance(diagram_td, str)
    assert is_str_td is True

    diagram_lr = _render_workflow_mermaid(
        None,
        demo_wf,
        direction="LR",
        highlight_cp=True,
        highlight_nodes={"validate_order"},
    )
    is_str_lr = isinstance(diagram_lr, str)
    assert is_str_lr is True

    mock_log = MagicMock()
    completed = _execute_saga_simulation(None, demo_wf, mock_log)
    step_count = len(completed)
    assert step_count == 3

    none_res = _render_workflow_mermaid(None, None)
    has_empty = "No workflow diagram available" in none_res
    assert has_empty is True

    empty_completed = _execute_saga_simulation(None, None, mock_log)
    empty_len = len(empty_completed)
    assert empty_len == 0

    client = Client(page("/test-workflow-controls"))
    with client.layout.default_slot:
        _render_workflow_tab(container)

    reset_btns = [
        e
        for e in client.elements.values()
        if isinstance(e, ui.button) and e._props.get("label") == "Reset Highlights"
    ]
    reset_btn_count = len(reset_btns)
    assert reset_btn_count == 1
    reset_listener = list(reset_btns[0]._event_listeners.values())[0]
    reset_handler = reset_listener.handler
    assert callable(reset_handler)
    if callable(reset_handler):
        reset_handler(None)

    dir_selects = [
        e
        for e in client.elements.values()
        if isinstance(e, ui.select) and e._props.get("label") == "Layout Direction"
    ]
    has_dir = len(dir_selects) == 1
    assert has_dir is True
    dir_selects[0].set_value("LR")

    cp_switches = [
        e
        for e in client.elements.values()
        if isinstance(e, ui.switch) and getattr(e, "text", "") == "Critical Path"
    ]
    has_cp = len(cp_switches) == 1
    assert has_cp is True
    cp_switches[0].set_value(True)


@pytest.mark.anyio
async def test_devtools_with_execution_pipeline_port():
    """Verify devtools dashboard, CQRS tab, ping, and mermaid with ExecutionPipelinePort."""

    @dataclass(frozen=True)
    class TestPingCommand(Command):
        message: str = ""

    @dataclass(frozen=True)
    class TestPingQuery(Query[str]):
        query_id: str = ""

    mock_port = MagicMock(spec=ExecutionPipelinePort)
    mock_port.get_registered_commands.return_value = {
        "TestPingCommand": TestPingCommand
    }
    mock_port.get_registered_queries.return_value = {"TestPingQuery": TestPingQuery}
    mock_port.execute.return_value = "PONG: Port"

    container = Container()
    container.add_instance(mock_port, declared_class=ExecutionPipelinePort)

    # 1. Render CQRS messages with port in container
    client = Client(page("/test-cqrs-port"))
    with client.layout.default_slot:
        _render_cqrs_messages(container)

    # 2. Test ping dispatch via port
    log_output = MagicMock()
    await _dispatch_ping("hello port", container, mock_port, [], log_output)
    mock_port.execute.assert_called_once()
    assert any("✅ [SUCCESS]" in call[0][0] for call in log_output.push.call_args_list)

    # 3. Test mermaid generation via port
    lines: list[str] = []
    has_cqrs, cmds, qrys = _build_mermaid_cqrs(container, lines)
    assert has_cqrs is True
    assert "TestPingCommand" in cmds
    assert "TestPingQuery" in qrys

    # 4. Test fallback to execute_by_name when no ping class registered
    mock_port_fallback = MagicMock(spec=ExecutionPipelinePort)
    mock_port_fallback.get_registered_commands.return_value = {}
    mock_port_fallback.execute_by_name.return_value = "PONG: Name"
    container_fallback = Container()
    container_fallback.add_instance(
        mock_port_fallback, declared_class=ExecutionPipelinePort
    )
    log_output_fallback = MagicMock()
    await _dispatch_ping(
        "hello fallback",
        container_fallback,
        mock_port_fallback,
        [],
        log_output_fallback,
    )
    mock_port_fallback.execute_by_name.assert_called_once()


def test_resolve_static_dir_and_sentry_env(monkeypatch: pytest.MonkeyPatch):
    """Verify _resolve_static_dir and sentry environment fallback logic."""
    static_dir = _resolve_static_dir()
    assert static_dir is None or static_dir.is_dir()

    monkeypatch.setenv(
        "SENTRY_DSN", "https://abcdef1234567890abcdef1234567890@sentry.io/12345"
    )
    container = Container()
    client = Client(page("/test-sentry-card-env"))
    with client.layout.default_slot:
        _render_observability_tab(container)

    has_sentry = _detect_sentry_presence(container, ["SentryLoggingAdapter"])
    assert has_sentry is True


@pytest.mark.anyio
async def test_devtools_pipeline_subclass_resolution_and_exceptions():
    """Verify pipeline subclass lookup and resilience against registry errors."""

    class CustomPipeline(ExecutionPipelinePort):
        def execute(
            self,
            instance: Any,
            output_format: str | None = None,
        ) -> Any:
            return "executed"

        def execute_by_name(
            self,
            name: str,
            payload: dict[str, Any],
            output_format: str | None = None,
        ) -> Any:
            return "executed_by_name"

        def get_registered_commands(self) -> dict[str, type[Command]]:
            raise RuntimeError("commands unavailable")

        def get_registered_queries(self) -> dict[str, type[Query[Any]]]:
            raise RuntimeError("queries unavailable")

    custom_pipeline = CustomPipeline()
    container = Container()
    container.add_instance(custom_pipeline, declared_class=CustomPipeline)

    client = Client(page("/test-custom-pipeline"))
    with client.layout.default_slot:
        _render_cqrs_messages(container)

    lines: list[str] = []
    has_cqrs, cmds, qrys = _build_mermaid_cqrs(container, lines)
    assert has_cqrs is False
    assert len(cmds) == 0
    assert len(qrys) == 0

    log_output = MagicMock()
    await _dispatch_ping("ping", container, None, [], log_output)
    assert any("✅ [SUCCESS]" in call[0][0] for call in log_output.push.call_args_list)

    # Test broken CommandRegistry / QueryRegistry
    container_broken = Container()

    class BrokenCmdRegistry:
        @property
        def all(self) -> dict[str, Any]:
            raise RuntimeError("broken cmd all")

    class BrokenQryRegistry:
        @property
        def all(self) -> dict[str, Any]:
            raise RuntimeError("broken qry all")

    BrokenCmdRegistry.__name__ = "CommandRegistry"
    BrokenQryRegistry.__name__ = "QueryRegistry"

    cmd_broken = BrokenCmdRegistry()
    qry_broken = BrokenQryRegistry()
    container_broken.add_instance(cmd_broken, declared_class=BrokenCmdRegistry)
    container_broken.add_instance(qry_broken, declared_class=BrokenQryRegistry)

    with client.layout.default_slot:
        _render_cqrs_messages(container_broken)
    _build_mermaid_cqrs(container_broken, lines)


@pytest.mark.anyio
async def test_simulation_branches_and_sync_safe(monkeypatch: pytest.MonkeyPatch):
    """Verify simulation non-completed status, failure logging, and sync safe worker."""
    # 1. Non-COMPLETED status
    mock_orch = MagicMock()
    mock_orch.simulate.return_value = MagicMock(
        status="FAILED", completed_steps=["step_fail"], outputs={"error": "aborted"}
    )
    log_output = MagicMock()
    wf_mock = MagicMock()
    wf_mock.name = "failing_workflow"

    completed = _execute_saga_simulation(mock_orch, wf_mock, log_output)
    assert completed == ["step_fail"]
    assert any("⚠️ [WARNING]" in call[0][0] for call in log_output.push.call_args_list)

    # 2. Simulation exception
    mock_orch_err = MagicMock()
    mock_orch_err.simulate.side_effect = RuntimeError("Simulation engine crashed")
    log_output.reset_mock()
    completed_err = _execute_saga_simulation(mock_orch_err, wf_mock, log_output)
    assert completed_err == []
    assert any("❌ [ERROR]" in call[0][0] for call in log_output.push.call_args_list)

    # 3. _run_sync_safe within running event loop
    def simple_sync_add(a: int, b: int) -> int:
        return a + b

    result = _run_sync_safe(simple_sync_add, 10, 20)
    assert result == 30

    # 4. _resolve_static_dir fallback on exception
    monkeypatch.setattr(
        "importlib.resources.files",
        MagicMock(side_effect=ModuleNotFoundError("package not found")),
    )
    fallback_dir = _resolve_static_dir()
    assert fallback_dir is None or fallback_dir.is_dir()
