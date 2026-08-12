from typing import Any
from unittest.mock import MagicMock

import grpc
import pytest
from hexastack_grpc.infra.config import HexastackGrpcConfig
from hexastack_grpc.infra.decorators import (
    get_grpc_registry,
    grpc_service,
)


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_grpc_registry()
    reg.clear()
    yield
    reg.clear()


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
