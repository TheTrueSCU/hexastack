"""Unit tests for NiceGUI DevTools dashboard."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from rodi import Container
from starlette.routing import Mount

from hexastack_core.domain import Command
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_ui.adapters.nicegui.devtools import mount_devtools_dashboard


def test_mount_devtools_dashboard():
    """Verify mount_devtools_dashboard attaches to FastAPI app and page renders."""
    from nicegui import core

    app = FastAPI()
    container = Container()
    pipeline = MagicMock(spec=ExecutionPipeline)

    mount_devtools_dashboard(
        app, container=container, pipeline=pipeline, path="/_devtools"
    )

    assert any(isinstance(r, Mount) for r in app.routes)
    assert len(core.app.routes) > 0


def test_render_internal_tabs():
    """Verify internal rendering helpers execute cleanly across container states."""
    from nicegui import Client
    from nicegui.page import page

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry
    from hexastack_cqrs.ports.buses import CommandBusPort
    from hexastack_ui.adapters.nicegui.devtools import (
        _render_container_tab,
        _render_cqrs_messages,
        _render_cqrs_tab,
        _render_flags_tab,
        _render_live_runner,
        _render_middleware_chain,
    )

    client = Client(page("/test-render-tabs"))
    with client.layout.default_slot:
        empty_container = Container()
        _render_cqrs_messages(empty_container)
        _render_middleware_chain([])
        _render_live_runner(empty_container, None, [])
        _render_cqrs_tab(empty_container, None)
        _render_flags_tab(empty_container)
        _render_container_tab(empty_container)

        container = Container()
        cmd_reg = CommandRegistry()
        qry_reg = QueryRegistry()
        from hexastack_core.domain.command import Command as BaseCmd
        from hexastack_core.domain.query import Query as BaseQry

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

        pipeline_mock = MagicMock(spec=ExecutionPipeline)
        pipeline_mock.execute = MagicMock(return_value="executed-ok")

        class AuthTestMiddleware:
            pass

        _render_cqrs_messages(container)
        _render_middleware_chain([mw, AuthTestMiddleware()])
        _render_live_runner(container, pipeline_mock, [mw])
        _render_cqrs_tab(container, pipeline=pipeline_mock)
        _render_flags_tab(container)
        _render_container_tab(container)


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
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_ui.adapters.nicegui.devtools import _dispatch_ping

    log_output = MagicMock()

    # 1. Pipeline + Registered Ping command
    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingDemoCommand(Command):
        message: str = ""

    creg.register(PingDemoCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline = MagicMock(spec=ExecutionPipeline)
    pipeline.execute = MagicMock(return_value="PONG: Direct")
    container.add_instance(pipeline, declared_class=ExecutionPipeline)

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
    pipeline_direct = MagicMock(spec=ExecutionPipeline)
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
    pipeline_err = MagicMock(spec=ExecutionPipeline)
    pipeline_err.execute_by_name.side_effect = RuntimeError("DB connection dropped")
    await _dispatch_ping("fail", Container(), pipeline_err, [], log_output)
    assert (
        "❌ [ERROR] Execution failed: DB connection dropped"
        in log_output.push.call_args_list[-1][0][0]
    )


def test_render_middleware_chain_elements(monkeypatch):
    """Verify middleware chain chips, icons, and handler badge."""
    from nicegui import Client, ui
    from nicegui.page import page

    from hexastack_ui.adapters.nicegui.devtools import _render_middleware_chain

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
    from nicegui import Client
    from nicegui.page import page

    from hexastack_ui.adapters.nicegui.devtools import _render_devtools_content

    container = Container()
    pipeline = MagicMock(spec=ExecutionPipeline)

    client = Client(page("/test-devtools-full"))
    with client.content:
        _render_devtools_content(container, pipeline, "Hexastack DevTools Full Test")


def test_render_table_structures_and_schemas(monkeypatch):
    """Verify table structures, column definitions, and row formatting across tabs."""
    from nicegui import Client, ui
    from nicegui.page import page

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.domain.command import Command as BaseCmd
    from hexastack_core.domain.query import Query as BaseQry
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry
    from hexastack_ui.adapters.nicegui.devtools import (
        _render_container_tab,
        _render_cqrs_messages,
        _render_flags_tab,
    )

    captured_tables: list[dict] = []
    orig_table = ui.table

    def mock_table(*args, **kwargs):
        captured_tables.append(kwargs)
        return orig_table(*args, **kwargs)

    monkeypatch.setattr(ui, "table", mock_table)

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

        # 2. Feature flags table
        flags_adapter = InMemoryFeatureFlagAdapter({"feature_x": True, "quota": 42})
        container.add_instance(flags_adapter, declared_class=FeatureFlagPort)

        _render_flags_tab(container)
        flags_table = captured_tables[-1]
        assert len(flags_table["columns"]) == 2
        assert flags_table["columns"][0] == {
            "name": "flag",
            "label": "Flag Key",
            "field": "flag",
            "sortable": True,
        }
        assert flags_table["columns"][1] == {
            "name": "enabled",
            "label": "Status",
            "field": "enabled",
            "sortable": True,
        }
        assert flags_table["row_key"] == "flag"
        assert flags_table["pagination"] == {"rowsPerPage": 10}
        assert {"flag": "feature_x", "enabled": "True"} in flags_table["rows"]
        assert {"flag": "quota", "enabled": "42"} in flags_table["rows"]

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
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_ui.adapters.nicegui.devtools import _dispatch_ping

    log_output = MagicMock()
    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingStrictCommand(Command):
        number: int

    creg.register(PingStrictCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline = MagicMock(spec=ExecutionPipeline)
    container.add_instance(pipeline, declared_class=ExecutionPipeline)

    # Passing string "not_a_number" causes model_validate to fail for int field
    await _dispatch_ping("not_a_number", container, None, [], log_output)
    pipeline.execute.assert_not_called()
    assert any(
        "❌ [ERROR] Execution failed:" in call[0][0]
        for call in log_output.push.call_args_list
    )
