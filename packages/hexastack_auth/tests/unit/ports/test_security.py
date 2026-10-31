import inspect

import pytest

from hexastack_auth.ports.security import SecurityPort


def test_security_port_abstract():
    with pytest.raises(TypeError):
        SecurityPort()  # ty: ignore[call-non-callable]


def test_security_port_is_abstract() -> None:
    """Verify that SecurityPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(SecurityPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SecurityPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_security_port_abstract_methods() -> None:
    """Verify abstract methods on SecurityPort."""
    expected = {"create_token", "verify_token"}
    abstracts = SecurityPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
