"""Unit tests for NiceGUI UI presentation adapter and DevTools dashboard."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from rodi import Container
from starlette.routing import Mount

from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_fastapi.adapters.ui import (
    dispatch_command,
    dispatch_query,
    mount_devtools_dashboard,
    ui_page,
)


@dataclass(frozen=True)
class CreateItem(Command):
    name: str


@dataclass(frozen=True)
class GetItem(Query):
    item_id: str


@pytest.mark.anyio
async def test_dispatch_command():
    """Verify dispatch_command invokes pipeline.execute with command."""
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="created-123")

    cmd = CreateItem(name="Widget")
    result = await dispatch_command(pipeline_mock, cmd)

    assert result == "created-123"
    pipeline_mock.execute.assert_called_once_with(cmd)


@pytest.mark.anyio
async def test_dispatch_query():
    """Verify dispatch_query invokes pipeline.execute with query."""
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="widget-data")

    qry = GetItem(item_id="123")
    result = await dispatch_query(pipeline_mock, qry)

    assert result == "widget-data"
    pipeline_mock.execute.assert_called_once_with(qry)


def test_ui_page_decorator():
    """Verify ui_page decorates callable cleanly without errors."""

    @ui_page("/test-page", title="Test Page")
    def my_page():
        return "page-content"

    assert callable(my_page)


def test_mount_devtools_dashboard():
    """Verify mount_devtools_dashboard attaches to FastAPI app."""
    from nicegui import core

    app = FastAPI()
    container = Container()
    pipeline = MagicMock(spec=ExecutionPipeline)

    # Mount devtools
    mount_devtools_dashboard(
        app, container=container, pipeline=pipeline, path="/_devtools"
    )

    # FastAPI app has Mount object attached
    assert any(isinstance(r, Mount) for r in app.routes)
    # NiceGUI internal core app has registered routes
    assert len(core.app.routes) > 0


def test_render_internal_tabs():
    """Verify internal rendering helpers execute cleanly across container states."""
    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry
    from hexastack_cqrs.ports.buses import CommandBusPort
    from hexastack_fastapi.adapters.ui import (
        _render_container_tab,
        _render_cqrs_messages,
        _render_cqrs_tab,
        _render_flags_tab,
        _render_live_runner,
        _render_middleware_chain,
    )

    # 1. Empty container rendering
    empty_container = Container()
    _render_cqrs_messages(empty_container)
    _render_middleware_chain([])
    _render_live_runner(empty_container, None, [])
    _render_cqrs_tab(empty_container, None)
    _render_flags_tab(empty_container)
    _render_container_tab(empty_container)

    # 2. Populated container rendering
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
    _render_live_runner(container, None, [mw])
    _render_flags_tab(container)
    _render_container_tab(container)


@pytest.mark.anyio
async def test_dispatch_command_and_query_awaitable():
    """Verify dispatch_command and dispatch_query handle awaitable results."""

    async def async_res():
        return "async-val"

    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value=async_res())

    res_cmd = await dispatch_command(pipeline_mock, CreateItem(name="AsyncWidget"))
    assert res_cmd == "async-val"

    pipeline_mock.execute = MagicMock(return_value=async_res())
    res_qry = await dispatch_query(pipeline_mock, GetItem(item_id="async-123"))
    assert res_qry == "async-val"


@pytest.mark.anyio
async def test_render_live_runner_ping_execution():
    """Verify _run_ping callback executes successfully with registered Ping command and pipeline."""
    from nicegui import ui

    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_fastapi.adapters.ui import _render_live_runner

    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingDemoCommand(Command):
        message: str = ""

    creg.register(PingDemoCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="PONG: Hello")
    container.add_instance(pipeline_mock, declared_class=ExecutionPipeline)

    with ui.card():
        _render_live_runner(container, pipeline_mock, [])

    # Find the button in NiceGUI client and trigger on_click
    for element in ui.context.client.layout.default_slot.children:
        slot = getattr(element, "default_slot", None)
        children = getattr(slot, "children", []) if slot is not None else []
        for child in children:
            if getattr(child, "text", "") == "Dispatch Ping Command":
                # Execute callback
                await child._props["on_click"]()
                pipeline_mock.execute.assert_called_once()


def test_check_nicegui_installed_missing():
    """Verify _check_nicegui_installed raises MissingDependencyError when nicegui is missing."""
    import sys
    from unittest.mock import patch

    from hexastack_core.domain.exceptions import MissingDependencyError
    from hexastack_fastapi.adapters.ui import _check_nicegui_installed

    with (
        patch.dict(sys.modules, {"nicegui": None}),
        pytest.raises(MissingDependencyError, match="NiceGUI is required"),
    ):
        _check_nicegui_installed()
