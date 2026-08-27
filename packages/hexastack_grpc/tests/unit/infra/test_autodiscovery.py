import types
from typing import Any
from unittest.mock import MagicMock

from hexastack_grpc.infra.autodiscovery import (
    autodiscover_grpc_services,
)
from hexastack_grpc.infra.decorators import (
    grpc_service,
)
from hexastack_grpc.infra.registries.service import GrpcServiceRegistry


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


def test_grpc_visitor_ignores_non_decorated_objects():
    """Verify create_grpc_visitor ignores objects without _GRPC_SERVICE_ATTR."""
    from hexastack_grpc.infra.autodiscovery import create_grpc_visitor

    registry = GrpcServiceRegistry()
    visitor = create_grpc_visitor(registry)

    class PlainObj:
        pass

    dummy_mod = types.ModuleType("dummy_empty_grpc_mod")
    visitor(PlainObj, dummy_mod)
    assert len(registry._services) == 0
