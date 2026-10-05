import pytest

from hexastack_core.domain import Query
from hexastack_cqrs.infra.registries import QueryRegistry, QueryRegistryError


class _DummyQuery(Query[str]):
    query_id: str


def test_get_unregistered_raises():
    reg = QueryRegistry()
    with pytest.raises(QueryRegistryError):
        reg.get("NonExistent")


def test_register_and_get():
    reg = QueryRegistry()
    reg.register(_DummyQuery)
    assert reg.get("_DummyQuery") == _DummyQuery
