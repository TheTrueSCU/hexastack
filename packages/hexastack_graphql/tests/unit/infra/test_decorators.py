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
