from collections.abc import Iterator

import pytest

from hexastack_core.testing import isolate_registries
from hexastack_grpc.infra.decorators import get_grpc_registry


@pytest.fixture(autouse=True)
def auto_isolate_grpc_registry() -> Iterator[None]:
    """Autouse fixture ensuring gRPC service registry is clean before and after every test."""
    with isolate_registries(get_grpc_registry()):
        yield
