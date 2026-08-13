from collections.abc import Iterator

import pytest
from hexastack_core.testing import isolate_registries
from hexastack_db.infra.registries.metadata import clear_metadata_registry


class _MetadataRegistryWrapper:
    """Wrapper implementing ClearableRegistry for database metadata."""

    def clear(self) -> None:
        clear_metadata_registry()


_METADATA_REGISTRY = _MetadataRegistryWrapper()


@pytest.fixture(autouse=True)
def auto_isolate_db_metadata() -> Iterator[None]:
    """Autouse fixture ensuring database metadata registry is clean before and after every test."""
    with isolate_registries(_METADATA_REGISTRY):
        yield
