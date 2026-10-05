import pytest

from hexastack_auth.ports.security import SecurityPort


def test_security_port_abstract():
    with pytest.raises(TypeError):
        SecurityPort()  # ty: ignore[call-non-callable]
