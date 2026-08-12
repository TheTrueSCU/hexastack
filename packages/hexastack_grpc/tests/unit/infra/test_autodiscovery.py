import types
from typing import Any
from unittest.mock import MagicMock

import pytest
from hexastack_grpc.infra.autodiscovery import (
    autodiscover_grpc_services,
)
from hexastack_grpc.infra.decorators import (
    get_grpc_registry,
    grpc_service,
)
from hexastack_grpc.infra.registries.service import GrpcServiceRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_grpc_registry()
    reg.clear()
    yield
    reg.clear()


def test_autodiscover_grpc_services():
    mod = types.ModuleType("dummy_grpc_mod")
    mock_add = MagicMock()

    @grpc_service(mock_add, service_names=["dummy.Service"])
    class MyServicer:
        def Call(self, req: Any, ctx: Any) -> str:
            return "ok"

    setattr(mod, "MyServicer", MyServicer)  # noqa: B010

    custom_reg = GrpcServiceRegistry()
    autodiscover_grpc_services([mod], custom_reg)

    assert len(custom_reg._services) == 1
    assert custom_reg._services[0].servicer == MyServicer
    assert custom_reg._services[0].service_names == ["dummy.Service"]
