from collections.abc import Iterator

import pytest
from hexastack_core.testing import isolate_registries
from hexastack_graphql.infra.decorators import get_schema_registry


@pytest.fixture(autouse=True)
def auto_isolate_graphql_registry() -> Iterator[None]:
    """Autouse fixture ensuring GraphQL schema registry is clean before and after every test."""
    with isolate_registries(get_schema_registry()):
        yield
