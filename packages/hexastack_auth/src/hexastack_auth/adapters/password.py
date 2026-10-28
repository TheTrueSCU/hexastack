"""Password hashing and verification adapters.

Notes/Architectural Intent:
    Provides production-grade, cryptographically secure password derivation implementations
    (PBKDF2-HMAC-SHA256, Argon2id, and BCrypt) adhering to PasswordHasherPort.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any

from hexastack_auth.domain.exceptions import PasswordHashError
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_core.utils import require_dependency


def _require_argon2() -> Any:
    return require_dependency(
        "argon2",
        extra="argon2",
        package="hexastack-auth",
        feature_name="Argon2PasswordHasher",
    )


def _require_bcrypt() -> Any:
    return require_dependency(
        "bcrypt",
        extra="bcrypt",
        package="hexastack-auth",
        feature_name="BcryptPasswordHasher",
    )


class Pbkdf2PasswordHasher(PasswordHasherPort):
    """Secure password hasher using PBKDF2-HMAC-SHA256 from the standard library.

    Notes/Architectural Intent:
        Employs Python's built-in hashlib with 600,000 iterations (recommended by OWASP)
        and constant-time comparison via hmac.compare_digest to prevent timing attacks.
        Requires zero external C-extensions or binary dependencies.
    """

    def __init__(
        self,
        iterations: int = 600_000,
        hash_name: str = "sha256",
        salt_bytes: int = 16,
    ) -> None:
        """Initialize PBKDF2 hasher parameters.

        Args:
            iterations: Number of PBKDF2 iterations (default 600,000).
            hash_name: Name of digest algorithm (default 'sha256').
            salt_bytes: Size of generated salt in bytes (default 16).
        """
        self._iterations = iterations
        self._hash_name = hash_name
        self._salt_bytes = salt_bytes

    def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password with a cryptographically secure random salt.

        Args:
            plain_password: The plaintext password string to hash.

        Returns:
            Salted and hashed password formatted as 'pbkdf2:sha256:iterations$salt$hash'.

        Raises:
            PasswordHashError: If hashing computation fails.
        """
        if not plain_password:
            raise PasswordHashError("Password string cannot be empty.")

        try:
            salt = secrets.token_bytes(self._salt_bytes)
            derived = hashlib.pbkdf2_hmac(
                self._hash_name,
                plain_password.encode("utf-8"),
                salt,
                self._iterations,
            )
            salt_b64 = base64.b64encode(salt).decode("ascii")
            hash_b64 = base64.b64encode(derived).decode("ascii")
            return f"pbkdf2:{self._hash_name}:{self._iterations}${salt_b64}${hash_b64}"
        except Exception as exc:
            raise PasswordHashError(f"Password hashing failed: {exc}") from exc

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a stored PBKDF2 hash string.

        Args:
            plain_password: The plaintext password string to test.
            hashed_password: The stored hashed password string.

        Returns:
            True if the password matches the hash, False otherwise.

        Raises:
            PasswordHashError: If the hash string format is malformed.
        """
        if not plain_password or not hashed_password:
            return False

        try:
            algorithm_part, salt_b64, hash_b64 = hashed_password.split("$")
            scheme, hash_name, iterations_str = algorithm_part.split(":")
            if scheme != "pbkdf2":
                raise PasswordHashError(f"Unsupported password scheme '{scheme}'.")

            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected_hash = base64.b64decode(hash_b64.encode("ascii"))

            derived = hashlib.pbkdf2_hmac(
                hash_name,
                plain_password.encode("utf-8"),
                salt,
                iterations,
            )
            return hmac.compare_digest(derived, expected_hash)
        except (ValueError, TypeError) as exc:
            raise PasswordHashError(f"Invalid password hash format: {exc}") from exc
        except Exception as exc:
            raise PasswordHashError(f"Password verification failed: {exc}") from exc


class Argon2PasswordHasher(PasswordHasherPort):
    """Modern memory-hard password hasher powered by Argon2id (argon2-cffi).

    Notes/Architectural Intent:
        Implements the winner of the Password Hashing Competition (Argon2id),
        offering superior resilience against GPU and ASIC brute-force attacks.
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
    ) -> None:
        """Initialize Argon2 hasher parameters.

        Args:
            time_cost: Number of iterations.
            memory_cost: Memory usage in KiB.
            parallelism: Number of parallel threads.
        """
        self._time_cost = time_cost
        self._memory_cost = memory_cost
        self._parallelism = parallelism
        self._hasher: Any | None = None

    def _get_hasher(self) -> Any:
        if self._hasher is None:
            argon2 = _require_argon2()
            self._hasher = argon2.PasswordHasher(
                time_cost=self._time_cost,
                memory_cost=self._memory_cost,
                parallelism=self._parallelism,
            )
        return self._hasher

    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password using Argon2id.

        Args:
            plain_password: The plaintext password string to hash.

        Returns:
            Argon2-formatted hash string.

        Raises:
            PasswordHashError: If hashing fails.
        """
        if not plain_password:
            raise PasswordHashError("Password string cannot be empty.")
        try:
            hasher = self._get_hasher()
            return str(hasher.hash(plain_password))
        except Exception as exc:
            raise PasswordHashError(f"Argon2 hashing failed: {exc}") from exc

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against an Argon2 hash.

        Args:
            plain_password: The plaintext password string to test.
            hashed_password: The stored hashed password string.

        Returns:
            True if valid, False otherwise.
        """
        if not plain_password or not hashed_password:
            return False
        try:
            hasher = self._get_hasher()
            hasher.verify(hashed_password, plain_password)
            return True
        except Exception:
            return False


class BcryptPasswordHasher(PasswordHasherPort):
    """Industry-standard adaptive password hasher powered by bcrypt.

    Notes/Architectural Intent:
        Provides BCrypt key derivation with configurable work factor (cost).
    """

    def __init__(self, rounds: int = 12) -> None:
        """Initialize Bcrypt hasher parameters.

        Args:
            rounds: Logarithmic work factor (default: 12).
        """
        self._rounds = rounds

    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password using BCrypt.

        Args:
            plain_password: The plaintext password string to hash.

        Returns:
            BCrypt-formatted hash string.

        Raises:
            PasswordHashError: If hashing fails.
        """
        if not plain_password:
            raise PasswordHashError("Password string cannot be empty.")
        try:
            bcrypt_mod = _require_bcrypt()
            salt = bcrypt_mod.gensalt(rounds=self._rounds)
            hashed = bcrypt_mod.hashpw(plain_password.encode("utf-8"), salt)
            return hashed.decode("ascii")
        except Exception as exc:
            raise PasswordHashError(f"BCrypt hashing failed: {exc}") from exc

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a BCrypt hash.

        Args:
            plain_password: The plaintext password string to test.
            hashed_password: The stored hashed password string.

        Returns:
            True if valid, False otherwise.
        """
        if not plain_password or not hashed_password:
            return False
        try:
            bcrypt_mod = _require_bcrypt()
            return bool(
                bcrypt_mod.checkpw(
                    plain_password.encode("utf-8"),
                    hashed_password.encode("ascii"),
                )
            )
        except Exception:
            return False


__all__ = [
    "Argon2PasswordHasher",
    "BcryptPasswordHasher",
    "Pbkdf2PasswordHasher",
]
