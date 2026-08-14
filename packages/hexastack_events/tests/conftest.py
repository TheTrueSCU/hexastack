import pytest

from hexastack_core.utils.context import (
    set_user_context,
)
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage


@pytest.fixture
def outbox_storage() -> InMemoryOutboxStorage:
    """Fixture providing a fresh in-memory outbox storage."""
    return InMemoryOutboxStorage()


@pytest.fixture
def distributed_bus() -> InMemoryDistributedEventBus:
    """Fixture providing a fresh in-memory distributed event bus."""
    return InMemoryDistributedEventBus()


@pytest.fixture(autouse=True)
def clean_events_context():
    """Autouse fixture resetting user context between tests."""
    set_user_context(None)
    yield
    set_user_context(None)
