from unittest.mock import MagicMock, patch

import pytest
import strawberry
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container
from strawberry import Schema

from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_graphql.adapters.fastapi import (
    _require_fastapi,
    create_graphql_router,
    mount_graphql_router,
)
from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.infra.decorators import (
    graphql_query_type,
)


def test_fastapi_graphql_context_buses_resolution():
    @strawberry.type
    class ContextStatus:
        has_command_bus: bool
        has_query_bus: bool
        has_request: bool

    @graphql_query_type
    class ContextInspectionQuery:
        @strawberry.field
        def inspect_buses(
            self, info: strawberry.Info[GraphQLContext, None]
        ) -> ContextStatus:
            return ContextStatus(
                has_command_bus=info.context.command_bus is not None,
                has_query_bus=info.context.query_bus is not None,
                has_request=info.context.request is not None,
            )

    runtime = bootstrap(packages_to_scan=[__name__])
    schema = runtime.container.resolve(Schema)

    # Both buses explicit
    mock_cbus = MagicMock(spec=CommandBusPort)
    mock_qbus = MagicMock(spec=QueryBusPort)
    r1 = create_graphql_router(
        schema,
        container=runtime.container,
        command_bus=mock_cbus,
        query_bus=mock_qbus,
    )
    assert r1.graphql_ide == "graphiql"
    app1 = FastAPI()
    app1.include_router(r1, prefix="/g1")
    c1 = TestClient(app1)
    res1 = c1.post(
        "/g1",
        json={"query": "{ inspectBuses { hasCommandBus hasQueryBus hasRequest } }"},
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["inspectBuses"] == {
        "hasCommandBus": True,
        "hasQueryBus": True,
        "hasRequest": True,
    }

    # Container without CommandBusPort or QueryBusPort
    empty_c = Container()
    r2 = create_graphql_router(schema, container=empty_c, graphiql=False)
    app2 = FastAPI()
    app2.include_router(r2, prefix="/g2")
    c2 = TestClient(app2)
    res2 = c2.post(
        "/g2",
        json={"query": "{ inspectBuses { hasCommandBus hasQueryBus hasRequest } }"},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["inspectBuses"] == {
        "hasCommandBus": False,
        "hasQueryBus": False,
        "hasRequest": True,
    }


def test_fastapi_graphql_router_mounting():
    @graphql_query_type
    class HealthQuery:
        @strawberry.field
        def check_context(self, info: strawberry.Info[GraphQLContext, None]) -> str:
            assert info.context.container is not None
            assert info.context.request is not None
            return "ContextValid"

        @strawberry.field
        def status(self) -> str:
            return "OK"

    runtime = bootstrap(packages_to_scan=[__name__])
    schema = runtime.container.resolve(Schema)

    # 1. create_graphql_router with explicit buses
    mock_cbus = MagicMock(spec=CommandBusPort)
    mock_qbus = MagicMock(spec=QueryBusPort)
    router = create_graphql_router(
        schema,
        container=runtime.container,
        command_bus=mock_cbus,
        query_bus=mock_qbus,
        graphiql=True,
    )

    app = FastAPI()
    app.include_router(router, prefix="/graphql")

    client = TestClient(app)
    res = client.post("/graphql", json={"query": "{ status checkContext }"})
    assert res.status_code == 200
    assert res.json()["data"] == {"status": "OK", "checkContext": "ContextValid"}

    # 2. mount_graphql_router helper
    app2 = FastAPI()
    mount_graphql_router(
        app2, schema, container=runtime.container, path="/custom_gql", graphiql=False
    )
    client2 = TestClient(app2)
    res2 = client2.post("/custom_gql", json={"query": "{ status }"})
    assert res2.status_code == 200
    assert res2.json()["data"] == {"status": "OK"}

    # 3. create_graphql_router with DI container resolving buses dynamically
    container_with_buses = Container()
    container_with_buses.add_instance(mock_cbus, declared_class=CommandBusPort)
    container_with_buses.add_instance(mock_qbus, declared_class=QueryBusPort)

    router_di = create_graphql_router(
        schema,
        container=container_with_buses,
    )
    app3 = FastAPI()
    app3.include_router(router_di, prefix="/di_gql")
    client3 = TestClient(app3)
    res3 = client3.post("/di_gql", json={"query": "{ status checkContext }"})
    assert res3.status_code == 200
    assert res3.json()["data"] == {"status": "OK", "checkContext": "ContextValid"}

    # 4. create_graphql_router with empty container (failing resolve falls back to None)
    empty_container = Container()
    router_empty = create_graphql_router(
        schema,
        container=empty_container,
        graphiql=False,
    )
    assert router_empty.graphql_ide is None
    app4 = FastAPI()
    app4.include_router(router_empty, prefix="/empty_gql")
    client4 = TestClient(app4)
    res4 = client4.post("/empty_gql", json={"query": "{ status }"})
    assert res4.status_code == 200
    assert res4.json()["data"] == {"status": "OK"}

    # 5. Verify default mount_graphql_router path and router properties
    app5 = FastAPI()
    mount_graphql_router(app5, schema, container=runtime.container)
    client5 = TestClient(app5)
    res5 = client5.post("/graphql", json={"query": "{ status }"})
    assert res5.status_code == 200
    assert res5.json()["data"] == {"status": "OK"}


def test_require_fastapi_missing():
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(
            MissingDependencyError,
            match="fastapi is required for FastAPI GraphQL integration. Install via 'pip install hexastack-graphql\\[fastapi\\]'.",
        ) as exc_info,
    ):
        _require_fastapi()
    assert isinstance(exc_info.value, HexastackError)
