import strawberry
from hexastack_core.utils.context import (
    correlation_id_ctx,
    set_correlation_id,
)
from hexastack_graphql.infra.extensions import CorrelationExtension


def test_correlation_extension_injects_correlation_id():
    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = strawberry.Schema(
        query=Query,
        extensions=[CorrelationExtension],
    )

    token = set_correlation_id("req-trace-abc1234")
    try:
        result = schema.execute_sync("{ hello }")
        assert result.data == {"hello": "world"}
        assert result.extensions is not None
        assert result.extensions.get("correlation_id") == "req-trace-abc1234"
    finally:
        correlation_id_ctx.reset(token)
