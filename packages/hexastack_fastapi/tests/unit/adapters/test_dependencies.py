from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.domain.exceptions import DependencyResolutionError
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.adapters.dependencies import (
    get_container,
    get_pipeline,
)


def test_get_container_and_pipeline_success():
    container = Container()
    handler_reg = HandlerRegistry()
    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    app = FastAPI()
    app.state.container = container
    app.state.pipeline = pipeline

    @app.get("/test-deps")
    async def endpoint(
        c: Annotated[Container, Depends(get_container)],
        p: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    ):
        return {"container_ok": c is not None, "pipeline_ok": p is not None}

    client = TestClient(app)
    res = client.get("/test-deps")
    assert res.status_code == 200
    assert res.json() == {"container_ok": True, "pipeline_ok": True}


def test_get_container_missing():
    app = FastAPI()

    @app.get("/missing-container")
    async def endpoint(c: Annotated[Container, Depends(get_container)]):
        return {}

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/missing-container")
    assert res.status_code == 500


def test_get_dependencies_direct_invocation_raises():
    req = Request(scope={"type": "http", "app": FastAPI()})

    with pytest.raises(DependencyResolutionError):
        get_container(req)

    with pytest.raises(DependencyResolutionError):
        get_pipeline(req)


def test_get_pipeline_resolved_from_container():
    handler_reg = HandlerRegistry()
    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )
    container = Container()
    container.add_instance(pipeline)

    app = FastAPI()
    app.state.container = container

    @app.get("/pipeline-from-di")
    async def endpoint(
        p: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    ):
        return {"resolved": p is pipeline}

    client = TestClient(app)
    res = client.get("/pipeline-from-di")
    assert res.status_code == 200
    assert res.json() == {"resolved": True}
