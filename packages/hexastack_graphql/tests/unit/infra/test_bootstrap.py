import strawberry
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_graphql.infra.bootstrap import (
    GraphQLBootstrapper,
    GraphQLBootstrapResult,
)
from hexastack_graphql.infra.decorators import (
    graphql_query_type,
)


def test_graphql_bootstrapper_initialization():
    @graphql_query_type
    class AppQuery:
        @strawberry.field
        def status(self) -> str:
            return "READY"

    result = bootstrap(
        bootstrappers=[GraphQLBootstrapper()],
        auto_discover=False,
    )

    schema = result.container.resolve(strawberry.Schema)
    assert schema is not None

    res = schema.execute_sync("{ status }")
    assert res.data == {"status": "READY"}

    gql_res = result.get("graphql_result")
    assert isinstance(gql_res, GraphQLBootstrapResult)
    assert gql_res.schema is schema
