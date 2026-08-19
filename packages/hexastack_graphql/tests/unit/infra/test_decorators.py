from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_mutation,
    graphql_mutation_type,
    graphql_query,
    graphql_query_type,
)


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
        @feature_flag_field("graphql.beta_field")
        def beta_field(self, info: Info[GraphQLContext, None]) -> str:
            return "secret data"

        @strawberry.field
        @feature_flag_field(
            "graphql.beta_field", raise_error=False, fallback="fallback_val"
        )
        async def async_fallback(self, info: Info[GraphQLContext, None]) -> str:
            return "live data"

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
