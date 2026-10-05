import pytest

from hexastack_auth.ports.password import PasswordHasherPort


def test_password_hasher_port_abstract():
    with pytest.raises(TypeError):
        PasswordHasherPort()  # type: ignore[abstract]
