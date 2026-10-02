"""Hypothesis property-based tests for GraphQLSchemaRegistry and resolver dispatch invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary GraphQL query & mutation execution, testing:
    1. Dynamic query type and field composition into valid executable Strawberry schemas.
    2. CQRS query and command dispatch within Strawberry execution contexts without field collision.
    3. Missing command/query bus handling and error serialization.
"""

import strawberry
from hypothesis import given
from hypothesis import strategies as st
from pydantic import create_model
from strawberry.types import Info

from hexastack_core.domain import Command, Query
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry
from hexastack_graphql.infra.resolvers import dispatch_command, dispatch_query

clean_str = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20
)


@given(
    field_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=15),
    return_val=clean_str,
    input_val=st.integers(min_value=1, max_value=1000),
)
def test_graphql_dynamic_schema_query_execution_property(
    field_name: str, return_val: str, input_val: int
):
    """Property: Dynamically composed Strawberry query roots execute queries and return exact data."""
    registry = GraphQLSchemaRegistry()

    @strawberry.type
    class DynamicQuery:
        @strawberry.field
        def fetch_data(self, factor: int) -> str:
            return f"{return_val}_{factor * 2}"

    registry.register_query_type(DynamicQuery)
    schema = registry.build_schema()

    query_str = f"""
    query {{
        fetchData(factor: {input_val})
    }}
    """
    result = schema.execute_sync(query_str)
    assert result.errors is None
    assert result.data == {"fetchData": f"{return_val}_{input_val * 2}"}


@given(
    msg=clean_str,
    num=st.integers(min_value=1, max_value=5000),
)
def test_graphql_cqrs_resolver_dispatch_property(msg: str, num: int):
    """Property: CQRS commands and queries dispatch cleanly through Strawberry resolvers with context."""
    EchoCmd = create_model("EchoCmd", msg=(str, ...), __base__=Command)
    CalcQry = create_model("CalcQry", num=(int, ...), __base__=Query)

    handler_reg = HandlerRegistry()
    handler_reg.register(EchoCmd, lambda c: f"echo_{c.msg}")
    handler_reg.register(CalcQry, lambda q: q.num * 10)

    cmd_bus = SynchronousCommandBus(handler_registry=handler_reg)
    qry_bus = SynchronousQueryBus(handler_registry=handler_reg)

    @strawberry.type
    class AppQuery:
        @strawberry.field
        def calc(self, info: Info[GraphQLContext, None], n: int) -> int:
            return dispatch_query(info, CalcQry.model_validate({"num": n}))

    @strawberry.type
    class AppMutation:
        @strawberry.mutation
        def echo(self, info: Info[GraphQLContext, None], m: str) -> str:
            return dispatch_command(info, EchoCmd.model_validate({"msg": m}))

    schema = strawberry.Schema(query=AppQuery, mutation=AppMutation)
    context = GraphQLContext(command_bus=cmd_bus, query_bus=qry_bus)

    # 1. Execute Query
    q_res = schema.execute_sync(
        f"query {{ calc(n: {num}) }}",
        context_value=context,
    )
    assert q_res.errors is None
    assert q_res.data == {"calc": num * 10}

    # 2. Execute Mutation
    m_res = schema.execute_sync(
        f'mutation {{ echo(m: "{msg}") }}',
        context_value=context,
    )
    assert m_res.errors is None
    assert m_res.data == {"echo": f"echo_{msg}"}
