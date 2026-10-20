"""Unit tests for test server utilities."""

import pytest

from hexastack_fastapi.testing.server import (
    EphemeralServer,
    ephemeral_server,
    find_free_port,
)


def test_server_utilities_instantiation() -> None:
    """Verify ephemeral server instantiates with valid port and factory code."""
    port = find_free_port()
    is_int = isinstance(port, int)
    assert is_int is True
    is_positive = port > 0
    assert is_positive is True
    server = EphemeralServer(app_factory_code="import sys", port=port)
    assert server.port == port
    is_callable = callable(ephemeral_server)
    assert is_callable is True


def test_ephemeral_server_premature_exit() -> None:
    """Verify EphemeralServer detects premature process termination immediately."""
    port = find_free_port()
    server = EphemeralServer(
        app_factory_code="import sys; sys.stderr.write('fatal crash\\n'); sys.exit(42)",
        port=port,
    )
    with pytest.raises(RuntimeError) as exc_info:
        server.start(ready_path="/", timeout=5.0)

    err_msg = str(exc_info.value)
    has_code = "code 42" in err_msg
    assert has_code is True
    has_log = "fatal crash" in err_msg
    assert has_log is True
    is_stopped = server.proc is None
    assert is_stopped is True
