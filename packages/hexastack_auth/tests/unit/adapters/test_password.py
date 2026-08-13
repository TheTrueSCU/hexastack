import pytest
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.domain.exceptions import PasswordHashError


def test_pbkdf2_hasher_success(pbkdf2_hasher: Pbkdf2PasswordHasher):
    password = "SuperSecretPassword123!"
    hashed = pbkdf2_hasher.hash_password(password)

    assert hashed.startswith("pbkdf2:sha256:")
    assert pbkdf2_hasher.verify_password(password, hashed) is True
    assert pbkdf2_hasher.verify_password("WrongPassword", hashed) is False


def test_pbkdf2_hasher_empty_password(pbkdf2_hasher: Pbkdf2PasswordHasher):
    with pytest.raises(PasswordHashError):
        pbkdf2_hasher.hash_password("")

    assert pbkdf2_hasher.verify_password("", "some_hash") is False
    assert pbkdf2_hasher.verify_password("password", "") is False


def test_pbkdf2_hasher_invalid_format(pbkdf2_hasher: Pbkdf2PasswordHasher):
    with pytest.raises(PasswordHashError):
        pbkdf2_hasher.verify_password("password", "invalid_hash_string")
