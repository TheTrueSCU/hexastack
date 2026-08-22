"""Unit tests for test server utilities."""

from hexastack_fastapi.testing.server import (
    EphemeralServer,
    ephemeral_server,
    find_free_port,
)


def test_server_utilities_instantiation() -> None:
    port = find_free_port()
    assert isinstance(port, int)
    assert port > 0
    server = EphemeralServer(app_factory_code="import sys", port=port)
    assert server.port == port
    assert callable(ephemeral_server)
