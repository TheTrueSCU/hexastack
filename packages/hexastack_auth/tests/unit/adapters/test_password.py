"""Unit tests for password hashing adapters (PBKDF2, Argon2, BCrypt)."""

from unittest.mock import patch

import pytest

from hexastack_auth.adapters.password import (
    Argon2PasswordHasher,
    BcryptPasswordHasher,
    Pbkdf2PasswordHasher,
)
from hexastack_auth.domain.exceptions import PasswordHashError


def test_pbkdf2_hasher_custom_parameters():
    hasher = Pbkdf2PasswordHasher(iterations=10_000, hash_name="sha512", salt_bytes=32)
    pwd = "CustomPassword789!"
    hashed = hasher.hash_password(pwd)

    assert hashed.startswith("pbkdf2:sha512:10000$")
    res_correct = hasher.verify_password(pwd, hashed)
    assert res_correct is True
    res_wrong = hasher.verify_password("wrong", hashed)
    assert res_wrong is False


def test_pbkdf2_hasher_empty_and_none_password(pbkdf2_hasher: Pbkdf2PasswordHasher):
    with pytest.raises(PasswordHashError, match="cannot be empty"):
        pbkdf2_hasher.hash_password("")

    res_empty_pwd = pbkdf2_hasher.verify_password("", "some_hash")
    assert res_empty_pwd is False
    res_empty_hash = pbkdf2_hasher.verify_password("password", "")
    assert res_empty_hash is False


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


def test_pbkdf2_hasher_salt_uniqueness(pbkdf2_hasher: Pbkdf2PasswordHasher):
    pwd = "IdenticalPassword123!"
    hash1 = pbkdf2_hasher.hash_password(pwd)
    hash2 = pbkdf2_hasher.hash_password(pwd)

    # Two hashes of the same password must produce distinct salts and outputs
    assert hash1 != hash2
    res1 = pbkdf2_hasher.verify_password(pwd, hash1)
    assert res1 is True
    res2 = pbkdf2_hasher.verify_password(pwd, hash2)
    assert res2 is True


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

    res_correct = pbkdf2_hasher.verify_password(password, hashed)
    assert res_correct is True
    res_wrong = pbkdf2_hasher.verify_password("WrongPassword", hashed)
    assert res_wrong is False


def test_argon2_hasher_basic_and_verification():
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost=512, parallelism=1)
    pwd = "ArgonSecretPassword123!"  # pragma: allowlist secret
    hashed = hasher.hash_password(pwd)

    assert hashed.startswith("$argon2id$")
    res_valid = hasher.verify_password(pwd, hashed)
    assert res_valid is True
    res_invalid = hasher.verify_password("WrongPassword", hashed)
    assert res_invalid is False
    res_empty_pwd = hasher.verify_password("", hashed)
    assert res_empty_pwd is False
    res_empty_hash = hasher.verify_password(pwd, "")
    assert res_empty_hash is False
    res_corrupt_hash = hasher.verify_password(pwd, "$invalid$argon$hash")
    assert res_corrupt_hash is False


def test_argon2_hasher_empty_password_raises():
    hasher = Argon2PasswordHasher()
    with pytest.raises(PasswordHashError, match="cannot be empty"):
        hasher.hash_password("")


def test_argon2_hasher_hashing_error():
    hasher = Argon2PasswordHasher()
    with (
        patch.object(
            hasher, "_get_hasher", side_effect=RuntimeError("argon2 engine failure")
        ),
        pytest.raises(PasswordHashError, match="Argon2 hashing failed"),
    ):
        hasher.hash_password("Secret123")


def test_bcrypt_hasher_basic_and_verification():
    hasher = BcryptPasswordHasher(rounds=4)
    pwd = "BcryptSecretPassword123!"  # pragma: allowlist secret
    hashed = hasher.hash_password(pwd)

    assert hashed.startswith("$2")
    res_valid = hasher.verify_password(pwd, hashed)
    assert res_valid is True
    res_invalid = hasher.verify_password("WrongPassword", hashed)
    assert res_invalid is False
    res_empty_pwd = hasher.verify_password("", hashed)
    assert res_empty_pwd is False
    res_empty_hash = hasher.verify_password(pwd, "")
    assert res_empty_hash is False
    res_corrupt_hash = hasher.verify_password(pwd, "corrupted_hash")
    assert res_corrupt_hash is False


def test_bcrypt_hasher_empty_password_raises():
    hasher = BcryptPasswordHasher(rounds=4)
    with pytest.raises(PasswordHashError, match="cannot be empty"):
        hasher.hash_password("")


def test_bcrypt_hasher_hashing_error():
    hasher = BcryptPasswordHasher(rounds=4)
    with (
        patch(
            "hexastack_auth.adapters.password._require_bcrypt",
            side_effect=RuntimeError("bcrypt missing"),
        ),
        pytest.raises(PasswordHashError, match="BCrypt hashing failed"),
    ):
        hasher.hash_password("Secret123")
