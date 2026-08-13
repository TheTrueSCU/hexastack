import base64
import hashlib
import hmac
import secrets

from hexastack_auth.domain.exceptions import PasswordHashError
from hexastack_auth.ports.password import PasswordHasherPort


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


__all__ = [
    "Pbkdf2PasswordHasher",
]
