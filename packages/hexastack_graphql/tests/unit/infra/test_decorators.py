from inline_snapshot import snapshot

from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_mutation,
    graphql_mutation_type,
    graphql_query,
    graphql_query_type,
)


def test_feature_flag_field_decorator_sync_and_async():
    import strawberry
    from rodi import Container

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_graphql.domain.context import GraphQLContext
    from hexastack_graphql.infra.decorators import feature_flag_field

    flags = InMemoryFeatureFlagAdapter({"graphql.beta_field": False})
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)

    ctx = GraphQLContext(container=container)

    from strawberry.types import Info

    @strawberry.type
    class FeatureQuery:
        @strawberry.field
        @feature_flag_field(
            "graphql.beta_field", raise_error=False, fallback="fallback_val"
        )
        async def async_fallback(self, info: Info[GraphQLContext, None]) -> str:
            return "live data"

        @strawberry.field
        @feature_flag_field("graphql.beta_field")
        def beta_field(self, info: Info[GraphQLContext, None]) -> str:
            return "secret data"

    schema = strawberry.Schema(query=FeatureQuery)

    # 1. Sync field disabled with raise_error=True yields GraphQL errors
    res_disabled = schema.execute_sync("{ betaField }", context_value=ctx)
    assert res_disabled.errors is not None
    assert "disabled by feature flag 'graphql.beta_field'" in str(
        res_disabled.errors[0]
    )

    # 2. Async field disabled with fallback returns fallback value without error
    import asyncio

    res_async_disabled = asyncio.run(
        schema.execute("{ asyncFallback }", context_value=ctx)
    )
    assert res_async_disabled.errors is None
    assert res_async_disabled.data == {"asyncFallback": "fallback_val"}

    # 3. Dynamic enabling unlocks live data
    flags.set_flag("graphql.beta_field", True)
    res_enabled = schema.execute_sync("{ betaField }", context_value=ctx)
    assert res_enabled.errors is None
    assert res_enabled.data == {"betaField": "secret data"}

    res_async_enabled = asyncio.run(
        schema.execute("{ asyncFallback }", context_value=ctx)
    )
    assert res_async_enabled.errors is None
    assert res_async_enabled.data == {"asyncFallback": "live data"}


def test_graphql_decorators():
    registry = get_schema_registry()

    @graphql_query_type
    class CustomQuery:
        def hello(self) -> str:
            return "world"

    @graphql_mutation_type
    class CustomMutation:
        def mutate_val(self) -> int:
            return 42

    @graphql_query(name="pingQuery", description="Ping query endpoint")
    def ping() -> str:
        return "pong"

    @graphql_mutation(name="pingMutation", description="Ping mutation endpoint")
    def trigger() -> bool:
        return True

    assert CustomQuery in registry._query_types
    assert CustomMutation in registry._mutation_types
    assert "pingQuery" in registry._query_fields
    assert "pingMutation" in registry._mutation_fields

    schema = registry.build_schema()
    assert schema is not None
    assert str(schema).strip() == snapshot(
        """
type Mutation {
  \"\"\"Ping mutation endpoint\"\"\"
  pingMutation: Boolean!
}

type Query {
  \"\"\"Ping query endpoint\"\"\"
  pingQuery: String!
}
""".strip()
    )


def test_feature_flag_field_decorator_sync_fallback_and_async_error():
    """Verify sync fallback and async error branches of feature_flag_field."""
    import strawberry
    from rodi import Container
    from strawberry.types import Info

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_graphql.domain.context import GraphQLContext
    from hexastack_graphql.infra.decorators import feature_flag_field

    flags = InMemoryFeatureFlagAdapter({"graphql.flag": False})
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)
    ctx = GraphQLContext(container=container)

    @strawberry.type
    class ExtraFeatureQuery:
        @strawberry.field
        @feature_flag_field("graphql.flag", raise_error=False, fallback=999)
        def sync_fallback(self, info: Info[GraphQLContext, None]) -> int:
            return 123

        @strawberry.field
        @feature_flag_field("graphql.flag", raise_error=True)
        async def async_error(self, info: Info[GraphQLContext, None]) -> str:
            return "async ok"

    schema = strawberry.Schema(query=ExtraFeatureQuery)

    # 1. Sync fallback returns fallback without error
    res_sync = schema.execute_sync("{ syncFallback }", context_value=ctx)
    assert res_sync.errors is None
    assert res_sync.data == {"syncFallback": 999}

    # 2. Async error raises GraphQLError
    import asyncio

    res_async = asyncio.run(schema.execute("{ asyncError }", context_value=ctx))
    assert res_async.errors is not None
    assert "disabled by feature flag 'graphql.flag'" in str(res_async.errors[0])


def test_graphql_query_and_mutation_decorators():
    """Verify standalone @graphql_query and @graphql_mutation functions attach metadata."""
    from hexastack_graphql.infra.decorators import (
        _GRAPHQL_FIELD_ATTR,
        _GRAPHQL_TYPE_ATTR,
        get_schema_registry,
        graphql_mutation,
        graphql_mutation_type,
        graphql_query,
        graphql_query_type,
    )

    @graphql_query(name="ping_query", description="Ping query desc")
    def ping() -> str:
        return "pong"

    @graphql_mutation(name="ping_mutation", description="Ping mut desc")
    def mutate_ping() -> bool:
        return True

    class PlainQueryCls:
        pass

    class PlainMutationCls:
        pass

    q_type = graphql_query_type(PlainQueryCls)
    m_type = graphql_mutation_type(PlainMutationCls)

    assert getattr(ping, _GRAPHQL_FIELD_ATTR).name == "ping_query"
    assert getattr(mutate_ping, _GRAPHQL_FIELD_ATTR).name == "ping_mutation"
    assert getattr(q_type, _GRAPHQL_TYPE_ATTR).kind == "query"
    assert getattr(m_type, _GRAPHQL_TYPE_ATTR).kind == "mutation"

    reg = get_schema_registry()
    assert "ping_query" in reg._query_fields
    assert "ping_mutation" in reg._mutation_fields
