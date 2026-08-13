from hexastack_core.domain.exceptions import HexastackError
from hexastack_graphql.domain.exceptions import (
    GraphQLError,
    SchemaBuildingError,
)


def test_graphql_exceptions_hierarchy():
    err = SchemaBuildingError("Invalid schema")
    assert isinstance(err, GraphQLError)
    assert isinstance(err, HexastackError)
    assert str(err) == "Invalid schema"
