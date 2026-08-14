import pytest

from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.domain.exceptions import PasswordHashError


def test_pbkdf2_hasher_success(pbkdf2_hasher: Pbkdf2PasswordHasher):
    password = "SuperSecretPassword123!"
    hashed = pbkdf2_hasher.hash_password(password)

    # Format verification: pbkdf2:hash_name:iterations$salt$hash
    assert hashed.startswith(f"pbkdf2:sha256:{pbkdf2_hasher._iterations}$")
    parts = hashed.split("$")
    assert len(parts) == 3
    algo_part, salt_b64, hash_b64 = parts
    assert algo_part == f"pbkdf2:sha256:{pbkdf2_hasher._iterations}"
    assert len(salt_b64) > 10
    assert len(hash_b64) > 20

    assert pbkdf2_hasher.verify_password(password, hashed) is True
    assert pbkdf2_hasher.verify_password("WrongPassword", hashed) is False


def test_pbkdf2_hasher_custom_parameters():
    hasher = Pbkdf2PasswordHasher(iterations=10_000, hash_name="sha512", salt_bytes=32)
    pwd = "CustomPassword789!"
    hashed = hasher.hash_password(pwd)

    assert hashed.startswith("pbkdf2:sha512:10000$")
    assert hasher.verify_password(pwd, hashed) is True
    assert hasher.verify_password("wrong", hashed) is False


def test_pbkdf2_hasher_salt_uniqueness(pbkdf2_hasher: Pbkdf2PasswordHasher):
    pwd = "IdenticalPassword123!"
    hash1 = pbkdf2_hasher.hash_password(pwd)
    hash2 = pbkdf2_hasher.hash_password(pwd)

    # Two hashes of the same password must produce distinct salts and outputs
    assert hash1 != hash2
    assert pbkdf2_hasher.verify_password(pwd, hash1) is True
    assert pbkdf2_hasher.verify_password(pwd, hash2) is True


def test_pbkdf2_hasher_empty_and_none_password(pbkdf2_hasher: Pbkdf2PasswordHasher):
    with pytest.raises(PasswordHashError, match="cannot be empty"):
        pbkdf2_hasher.hash_password("")

    assert pbkdf2_hasher.verify_password("", "some_hash") is False
    assert pbkdf2_hasher.verify_password("password", "") is False


def test_pbkdf2_hasher_invalid_formats_and_schemes(pbkdf2_hasher: Pbkdf2PasswordHasher):
    # Invalid delimiter structure
    with pytest.raises(PasswordHashError, match="Invalid password hash format"):
        pbkdf2_hasher.verify_password("password", "invalid_hash_string")

    # Unsupported scheme
    with pytest.raises(PasswordHashError, match="Unsupported password scheme 'bcrypt'"):
        pbkdf2_hasher.verify_password(
            "password", "bcrypt:sha256:1000$c2FsdA==$aGFzaA=="
        )

    # Invalid non-integer iterations
    with pytest.raises(PasswordHashError, match="Invalid password hash format"):
        pbkdf2_hasher.verify_password(
            "password", "pbkdf2:sha256:notanint$c2FsdA==$aGFzaA=="
        )
