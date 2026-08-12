from hexastack_core.domain.generic import Generic
from hexastack_core.domain.query import Query


class GetItemQuery(Query[str]):
    item_id: str


def test_query_inheritance_and_properties():
    query = GetItemQuery(item_id="item-123")
    assert isinstance(query, Query)
    assert isinstance(query, Generic)
    assert query.item_id == "item-123"
