"""Port interfaces defining identifier obfuscation and public token encoding.

Notes/Architectural Intent:
    Decouples domain models and HTTP/GraphQL presentation layers from
    specific token encoding and obfuscation algorithms (e.g. Hashids, Base62).
    Prevents sequential identifier enumeration attacks while maintaining
    fast, indexed internal integer primary keys.
"""

from abc import ABC, abstractmethod


class IdObfuscatorPort(ABC):
    """Abstract port for reversible identifier obfuscation."""

    @abstractmethod
    def encode(self, number: int) -> str:
        """Encode an integer into an obfuscated, URL-safe token.

        Args:
            number: Non-negative integer to encode.

        Returns:
            URL-safe obfuscated string token.

        Raises:
            ValueError: If number is negative or cannot be encoded.
        """

    @abstractmethod
    def decode(self, token: str) -> int:
        """Decode an obfuscated token back into its original integer.

        Args:
            token: Obfuscated string token.

        Returns:
            Original integer identifier.

        Raises:
            ValueError: If token is invalid, malformed, or cannot be decoded.
        """

    @abstractmethod
    def encode_many(self, numbers: list[int] | tuple[int, ...]) -> str:
        """Encode multiple non-negative integers into a single composite token.

        Args:
            numbers: Sequence of non-negative integers to encode.

        Returns:
            URL-safe composite string token.

        Raises:
            ValueError: If sequence is empty, any number is negative, or cannot be encoded.
        """

    @abstractmethod
    def decode_many(self, token: str) -> tuple[int, ...]:
        """Decode a composite token back into its tuple of integers.

        Args:
            token: Composite string token.

        Returns:
            Tuple of original integer identifiers.

        Raises:
            ValueError: If token is invalid, malformed, or cannot be decoded.
        """


__all__ = [
    "IdObfuscatorPort",
]
