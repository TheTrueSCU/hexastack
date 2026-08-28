from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    """Abstract port interface for password hashing and cryptographic verification.

    Notes/Architectural Intent:
        Decouples credential verification from specific hashing algorithms
        (PBKDF2, Argon2, BCrypt), allowing zero-dependency fallbacks in testing
        and high-entropy key derivation in production.
    """

    @abstractmethod
    def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password.

        Args:
            plain_password: The plaintext password string to hash.

        Returns:
            Cryptographically salted and hashed password string.

        Raises:
            PasswordHashError: If hashing computation fails.
        """

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a stored hashed password.

        Args:
            plain_password: The plaintext password string to test.
            hashed_password: The stored hashed password string.

        Returns:
            True if the password matches the hash, False otherwise.

        Raises:
            PasswordHashError: If verification computation encounters an invalid format.
        """


__all__ = [
    "PasswordHasherPort",
]
