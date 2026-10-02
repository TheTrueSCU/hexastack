from unittest.mock import MagicMock

import grpc

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_grpc.infra.decorators import grpc_service


def test_grpc_bootstrapper():
    mock_add = MagicMock()

    @grpc_service(mock_add)
    class PingServicer:
        pass

    runtime = bootstrap(packages_to_scan=[__name__])

    # Verify grpc.Server in DI container
    server = runtime.container.resolve(grpc.Server)
    assert server is not None

    # Verify context properties
    assert "grpc_server" in runtime.properties
    assert "grpc_result" in runtime.properties
