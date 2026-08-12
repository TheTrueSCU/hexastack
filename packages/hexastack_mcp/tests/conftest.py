from collections.abc import Iterator

import pytest
from hexastack_core.testing import isolate_registries
from hexastack_mcp.infra.decorators import get_mcp_registry


@pytest.fixture(autouse=True)
def auto_isolate_mcp_registry() -> Iterator[None]:
    """Autouse fixture ensuring MCP server registry is clean before and after every test."""
    with isolate_registries(get_mcp_registry()):
        yield
