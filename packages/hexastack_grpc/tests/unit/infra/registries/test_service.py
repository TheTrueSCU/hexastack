from typing import Any
from unittest.mock import MagicMock

import grpc

from hexastack_grpc.infra.config import HexastackGrpcConfig
from hexastack_grpc.infra.decorators import (
    get_grpc_registry,
    grpc_service,
)


class DummyServicer:
    def DoWork(self, request: Any, context: Any) -> str:
        return "done"


def test_grpc_service_registry_build_server():
    mock_add_to_server = MagicMock()

    @grpc_service(mock_add_to_server, service_names=["test.DummyService"])
    class RegisteredServicer(DummyServicer):
        pass

    reg = get_grpc_registry()
    cfg = HexastackGrpcConfig(host="127.0.0.1", port=50055)

    server = reg.build_server(cfg)
    assert isinstance(server, grpc.Server)
    mock_add_to_server.assert_called_once()


def test_grpc_service_registry_container_resolution():
    """Verify _resolve_servicer_instance resolves from container or falls back to direct instantiation."""
    from rodi import Container

    from hexastack_grpc.infra.registries.service import GrpcServiceRegistry

    reg = GrpcServiceRegistry()

    class CustomServicer:
        def __init__(self, tag: str = "default"):
            self.tag = tag

    # 1. Instance already instantiated
    inst = CustomServicer(tag="pre-instantiated")
    assert reg._resolve_servicer_instance(inst, None) is inst

    # 2. Class resolved from container
    c = Container()
    c.add_instance(CustomServicer(tag="from-container"), declared_class=CustomServicer)
    res_c = reg._resolve_servicer_instance(CustomServicer, c)
    assert res_c.tag == "from-container"

    # 3. Class failing container resolve falls back to direct constructor
    c_empty = Container()
    res_fallback = reg._resolve_servicer_instance(CustomServicer, c_empty)
    assert res_fallback.tag == "default"

    # 4. Class without container
    res_no_c = reg._resolve_servicer_instance(CustomServicer, None)
    assert res_no_c.tag == "default"


def test_grpc_service_registry_build_server_error_handling():
    """Verify build_server raises ServiceRegistrationError on failure."""
    import pytest

    from hexastack_grpc.domain.exceptions import ServiceRegistrationError
    from hexastack_grpc.infra.registries.service import GrpcServiceRegistry

    reg = GrpcServiceRegistry()

    def failing_add(servicer, server):
        raise RuntimeError("boom")

    reg.register_service(DummyServicer, failing_add, ["failing.Service"])

    cfg = HexastackGrpcConfig()
    with pytest.raises(ServiceRegistrationError, match="Failed to attach"):
        reg.build_server(cfg)
