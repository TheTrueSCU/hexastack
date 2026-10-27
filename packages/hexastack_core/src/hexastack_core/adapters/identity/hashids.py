"""Hashids adapter implementing IdObfuscatorPort.

Notes/Architectural Intent:
    Provides reversible, URL-safe identifier obfuscation using the Hashids algorithm.
    Allows configuring custom salts (for multi-tenant isolation), minimum token
    lengths, and custom alphabets.
"""

from collections.abc import Sequence

from hexastack_core.ports.identity import IdObfuscatorPort

try:
    from hashids import Hashids
except ImportError:
    Hashids = None  # type: ignore[assignment,misc]


class HashidsAdapter(IdObfuscatorPort):
    """Reversible identifier obfuscator backed by Hashids."""

    def __init__(
        self,
        salt: str = "",
        min_length: int = 8,
        alphabet: str | None = None,
    ) -> None:
        """Initialize HashidsAdapter.

        Args:
            salt: Optional secret salt for domain/tenant separation.
            min_length: Minimum generated token character length. Defaults to 8.
            alphabet: Optional custom character set for generated tokens.

        Raises:
            ImportError: If the 'hashids' package is not installed.
            ValueError: If min_length is negative.
        """
        if Hashids is None:
            msg = (
                "The 'hashids' package is required to use HashidsAdapter. "
                "Install it with 'pip install hexastack-core[identity]'."
            )
            raise ImportError(msg)

        if min_length < 0:
            msg = f"min_length must be non-negative, got {min_length}"
            raise ValueError(msg)

        self._salt = salt
        self._min_length = min_length
        self._alphabet = alphabet

        kwargs: dict[str, object] = {
            "salt": salt,
            "min_length": min_length,
        }
        if alphabet is not None:
            kwargs["alphabet"] = alphabet

        self._hasher = Hashids(**kwargs)  # type: ignore[arg-type]

    def encode(self, number: int) -> str:
        """Encode an integer into an obfuscated token.

        Args:
            number: Non-negative integer to encode.

        Returns:
            Obfuscated string token.

        Raises:
            ValueError: If number is negative.
        """
        if number < 0:
            msg = f"Cannot encode negative integer: {number}"
            raise ValueError(msg)

        return str(self._hasher.encode(number))

    def decode(self, token: str) -> int:
        """Decode an obfuscated token back into its original integer.

        Args:
            token: Obfuscated string token.

        Returns:
            Decoded original integer.

        Raises:
            ValueError: If token is invalid or cannot be decoded.
        """
        if not token or not isinstance(token, str):
            msg = f"Invalid token format: {token!r}"
            raise ValueError(msg)

        decoded = self._hasher.decode(token)
        if not decoded:
            msg = f"Invalid or undecodable token: {token!r}"
            raise ValueError(msg)

        return int(decoded[0])

    def encode_many(self, numbers: Sequence[int]) -> str:
        """Encode multiple non-negative integers into a composite token.

        Args:
            numbers: Sequence of non-negative integers.

        Returns:
            Composite obfuscated string token.

        Raises:
            ValueError: If sequence is empty or any integer is negative.
        """
        if not numbers:
            msg = "Cannot encode empty sequence of numbers"
            raise ValueError(msg)

        for n in numbers:
            if n < 0:
                msg = f"Cannot encode negative integer in sequence: {n}"
                raise ValueError(msg)

        return str(self._hasher.encode(*numbers))

    def decode_many(self, token: str) -> tuple[int, ...]:
        """Decode a composite token back into a tuple of integers.

        Args:
            token: Composite string token.

        Returns:
            Tuple of original decoded integers.

        Raises:
            ValueError: If token is invalid or cannot be decoded.
        """
        if not token or not isinstance(token, str):
            msg = f"Invalid composite token format: {token!r}"
            raise ValueError(msg)

        decoded = self._hasher.decode(token)
        if not decoded:
            msg = f"Invalid or undecodable composite token: {token!r}"
            raise ValueError(msg)

        return tuple(int(x) for x in decoded)


__all__ = [
    "HashidsAdapter",
]
