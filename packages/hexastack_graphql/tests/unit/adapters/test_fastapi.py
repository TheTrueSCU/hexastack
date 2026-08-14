import strawberry
from fastapi import FastAPI
from fastapi.testclient import TestClient
from strawberry import Schema

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_graphql.adapters.fastapi import create_graphql_router
from hexastack_graphql.infra.decorators import (
    graphql_query_type,
)


def test_fastapi_graphql_router_mounting():
    @graphql_query_type
    class HealthQuery:
        @strawberry.field
        def status(self) -> str:
            return "OK"

    runtime = bootstrap(packages_to_scan=[__name__])
    schema = runtime.container.resolve(Schema)

    router = create_graphql_router(schema, container=runtime.container)
    app = FastAPI()
    app.include_router(router, prefix="/graphql")

    client = TestClient(app)
    res = client.post("/graphql", json={"query": "{ status }"})
    assert res.status_code == 200
    assert res.json()["data"] == {"status": "OK"}
