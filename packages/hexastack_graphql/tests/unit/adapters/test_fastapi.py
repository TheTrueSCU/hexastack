from dataclasses import dataclass

import pytest
import strawberry
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import query_handler
from hexastack_graphql.adapters.fastapi import mount_graphql_router
from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_query_type,
)
from strawberry.types import Info


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_schema_registry()
    reg.clear()
    yield
    reg.clear()


@dataclass(frozen=True)
class GetProductQuery(Query):
    product_id: str


@query_handler(GetProductQuery)
class GetProductHandler:
    def __call__(self, qry: GetProductQuery) -> dict[str, str]:
        return {"id": qry.product_id, "name": f"Product-{qry.product_id}"}


@strawberry.type
class ProductType:
    id: str
    name: str


def test_fastapi_graphql_router_execution():
    @graphql_query_type
    class RootQuery:
        @strawberry.field
        def product(
            self, info: Info[GraphQLContext, None], product_id: str
        ) -> ProductType:
            assert info.context.query_bus is not None
            res = info.context.query_bus.dispatch(
                GetProductQuery(product_id=product_id)
            )
            return ProductType(id=res["id"], name=res["name"])

    runtime = bootstrap(packages_to_scan=[__name__])
    schema = get_schema_registry().build_schema()

    app = FastAPI()
    mount_graphql_router(
        app=app,
        schema=schema,
        container=runtime.container,
        path="/graphql",
    )

    client = TestClient(app)
    response = client.post(
        "/graphql",
        json={"query": '{ product(productId: "p100") { id name } }'},
    )

    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data
    assert data["data"] == {
        "product": {
            "id": "p100",
            "name": "Product-p100",
        }
    }
