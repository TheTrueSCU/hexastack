from unittest.mock import MagicMock, patch

import pytest
import strawberry
from fastapi import FastAPI
from fastapi.testclient import TestClient
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


def test_fastapi_graphql_router_mounting():
    @graphql_query_type
    class HealthQuery:
        @strawberry.field
        def status(self) -> str:
            return "OK"

        @strawberry.field
        def check_context(self, info: strawberry.Info[GraphQLContext, None]) -> str:
            assert info.context.container is not None
            assert info.context.request is not None
            return "ContextValid"

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


def test_require_fastapi_missing():
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="fastapi is required") as exc_info,
    ):
        _require_fastapi()
    assert isinstance(exc_info.value, HexastackError)
