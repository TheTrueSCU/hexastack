from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.domain import Command, Generic, Query
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
from hexastack_fastapi.adapters.app import create_fastapi_app
from hexastack_fastapi.adapters.dependencies import (
    check_openapi_conformance,
    get_container,
    get_pipeline,
)
from hexastack_fastapi.adapters.routing import CqrsRouter
from hexastack_fastapi.infra.config import HexastackFastApiConfig


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


def test_get_feature_flags_and_require_feature_guard():
    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_fastapi.adapters.dependencies import (
        get_feature_flags,
        require_feature,
    )

    flags = InMemoryFeatureFlagAdapter({"api.beta_checkout": False})
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)

    app = FastAPI()
    app.state.container = container

    @app.get(
        "/beta-checkout", dependencies=[Depends(require_feature("api.beta_checkout"))]
    )
    async def beta_endpoint():
        return {"status": "beta active"}

    client = TestClient(app)

    # 1. Disabled flag yields 404
    res_disabled = client.get("/beta-checkout")
    assert res_disabled.status_code == 404
    assert res_disabled.json() == {"detail": "Feature 'api.beta_checkout' is disabled."}

    # 2. Enabling flag dynamically unlocks route
    flags.set_flag("api.beta_checkout", True)
    res_enabled = client.get("/beta-checkout")
    assert res_enabled.status_code == 200
    assert res_enabled.json() == {"status": "beta active"}

    # 3. Direct request with default fallback
    plain_req = Request(scope={"type": "http", "app": FastAPI()})
    default_flags = get_feature_flags(plain_req)
    assert default_flags is not None


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


class _TestCreateItem(Command):
    name: str
    amount: int


class _TestGetItem(Query):
    item_id: str


class _TestItemDTO(Generic):
    status: str
    name: str


def test_check_openapi_conformance_smoke() -> None:
    handler_reg = HandlerRegistry()
    presenter_reg = PresenterRegistry()

    handler_reg.register(
        _TestCreateItem, lambda cmd: _TestItemDTO(status="created", name=cmd.name)
    )
    handler_reg.register(
        _TestGetItem, lambda q: _TestItemDTO(status="found", name=q.item_id)
    )

    cmd_reg = CommandRegistry()
    query_reg = QueryRegistry()

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=cmd_reg,
        query_registry=query_reg,
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    container = Container()
    container.add_instance(pipeline)

    router = CqrsRouter(prefix="/items")
    router.add_command("/create", _TestCreateItem, summary="Create item")
    router.add_query("/get", _TestGetItem, summary="Get item")

    config = HexastackFastApiConfig(title="FuzzTestAPI", version="1.0.0")
    app = create_fastapi_app(config=config, container=container, pipeline=pipeline)
    app.include_router(router)

    # 1. Structural OpenAPI Schema Conformance
    check_openapi_conformance(app)

    # 2. Schemathesis operation discovery validation
    import schemathesis

    schema = schemathesis.openapi.from_asgi("/openapi.json", app)
    paths = set(schema)
    assert "/items/create" in paths
    assert "/items/get" in paths


def test_fastapi_dependencies_isolated_resolvers():
    """Verify isolated dependency helper functions directly."""
    from unittest.mock import MagicMock

    from fastapi import HTTPException, Request
    from rodi import Container

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_fastapi.adapters.dependencies import (
        get_container,
        get_pipeline,
        require_feature,
    )

    # 1. Pipeline from container
    container = Container()
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    container.add_instance(pipeline_mock, declared_class=ExecutionPipeline)

    req = MagicMock(spec=Request)
    req.app.state.pipeline = None
    req.app.state.container = container

    assert get_pipeline(req) is pipeline_mock
    assert get_container(req) is container

    # 2. require_feature enabled and disabled
    flags = InMemoryFeatureFlagAdapter({"feature.gated": False})
    container.add_instance(flags, declared_class=FeatureFlagPort)
    req.state.container = container

    dep_fn = require_feature("feature.gated")
    import asyncio

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dep_fn(req))
    assert exc_info.value.status_code == 404

    flags.set_flag("feature.gated", True)
    # When enabled, does not raise
    asyncio.run(dep_fn(req))
