from dataclasses import dataclass

import strawberry
from strawberry.types import Info

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_mutation_type,
    graphql_query_type,
)
from hexastack_graphql.infra.resolvers import (
    dispatch_command,
    dispatch_query,
)


@dataclass(frozen=True)
class FindItemQuery(Query):
    sku: str


@query_handler(FindItemQuery)
class FindItemHandler:
    def __call__(self, qry: FindItemQuery) -> str:
        return f"Found SKU: {qry.sku}"


@dataclass(frozen=True)
class UpdateStockCommand(Command):
    sku: str
    quantity: int


@command_handler(UpdateStockCommand)
class UpdateStockHandler:
    def __call__(self, cmd: UpdateStockCommand) -> str:
        return f"Updated {cmd.sku} with {cmd.quantity}"


def test_resolve_query_and_command_helpers():
    @graphql_query_type
    class QueryRoot:
        @strawberry.field
        def item(self, info: Info[GraphQLContext, None], sku: str) -> str:
            return dispatch_query(info, FindItemQuery(sku=sku))

    @graphql_mutation_type
    class MutationRoot:
        @strawberry.mutation
        def update_stock(
            self, info: Info[GraphQLContext, None], sku: str, quantity: int
        ) -> str:
            return dispatch_command(
                info, UpdateStockCommand(sku=sku, quantity=quantity)
            )

    runtime = bootstrap(packages_to_scan=[__name__])
    schema = get_schema_registry().build_schema()

    ctx = GraphQLContext(
        container=runtime.container,
        query_bus=runtime.container.resolve(QueryBusPort),
        command_bus=runtime.container.resolve(CommandBusPort),
    )

    q_res = schema.execute_sync('{ item(sku: "SKU-999") }', context_value=ctx)
    assert q_res.errors is None
    assert q_res.data == {"item": "Found SKU: SKU-999"}

    m_res = schema.execute_sync(
        'mutation { updateStock(sku: "SKU-999", quantity: 50) }',
        context_value=ctx,
    )
    assert m_res.errors is None
    assert m_res.data == {"updateStock": "Updated SKU-999 with 50"}
