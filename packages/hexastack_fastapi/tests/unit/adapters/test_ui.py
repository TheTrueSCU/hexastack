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
    cmd_reg.register(CreateItem)
    qry_reg.register(GetItem)

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

    _render_cqrs_messages(container)
    _render_middleware_chain([mw])
    _render_live_runner(container, pipeline_mock, [mw])
    _render_cqrs_tab(container, pipeline_mock)
    _render_flags_tab(container)
    _render_container_tab(container)


@pytest.mark.anyio
async def test_devtools_page_and_ping_runner_execution():
    """Verify devtools page rendering callback and async ping runner callback."""

    app = FastAPI()
    container = Container()
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="pong-success")
    pipeline_mock.execute_by_name = MagicMock(return_value="pong-by-name-success")

    mount_devtools_dashboard(
        app, container=container, pipeline=pipeline_mock, path="/_devtools_test"
    )

    # Find registered page handler for /_devtools_test
    for route in app.routes:
        if getattr(route, "path", None) == "/_devtools_test":
            endpoint = getattr(route, "endpoint", None)
            if endpoint and callable(endpoint):
                endpoint()

    # Directly test _render_live_runner button callback
    from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
    from hexastack_fastapi.adapters.ui import _render_live_runner

    mw = CorrelationMiddleware()
    _render_live_runner(container, pipeline_mock, [mw])
    _render_live_runner(container, None, [mw])
