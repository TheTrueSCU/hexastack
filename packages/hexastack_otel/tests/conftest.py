import pytest

from hexastack_core.utils.context import (
    set_user_context,
)
from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter
from hexastack_otel.adapters.tracing.otel import OtelTracingAdapter


@pytest.fixture(autouse=True)
def clean_context():
    """Autouse fixture resetting user context between tests."""
    set_user_context(None)
    yield
    set_user_context(None)


@pytest.fixture
def in_memory_tracer() -> InMemoryTracingAdapter:
    """Fixture providing a fresh InMemoryTracingAdapter."""
    return InMemoryTracingAdapter()


@pytest.fixture
def otel_tracer() -> OtelTracingAdapter:
    """Fixture providing an OtelTracingAdapter."""
    return OtelTracingAdapter(service_name="test-service")
