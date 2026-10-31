import inspect

import pytest

from hexastack_auth.ports.password import PasswordHasherPort


def test_password_hasher_port_abstract():
    with pytest.raises(TypeError):
        PasswordHasherPort()  # ty: ignore[call-non-callable]


def test_password_hasher_port_is_abstract() -> None:
    """Verify that PasswordHasherPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(PasswordHasherPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        PasswordHasherPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_password_hasher_port_abstract_methods() -> None:
    """Verify abstract methods on PasswordHasherPort."""
    expected = {"hash_password", "verify_password"}
    abstracts = PasswordHasherPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
