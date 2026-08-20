"""Property-based fuzzing tests for TodoItem domain invariants."""

from hypothesis import given
from hypothesis import strategies as st

from todo_app.domain.models import Priority, TodoItem


@given(
    title=st.text(min_size=1, max_size=200),
    description=st.text(max_size=500),
    priority=st.sampled_from(Priority),
)
def test_todo_item_invariants(title: str, description: str, priority: Priority):
    """Assert entity maintains state invariants regardless of input variations."""
    item = TodoItem(title=title, description=description, priority=priority)
    assert item.title == title
    assert item.description == description
    assert item.priority == priority
    assert not item.completed
    assert len(item.id) > 0
