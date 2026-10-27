"""In-memory reference identifier obfuscator implementing IdObfuscatorPort.

Notes/Architectural Intent:
    Provides a lightweight, zero-external-dependency reference implementation
    using Base62 encoding. Acts as the naive reference oracle in dual-implementation
    verification suites (Hypothesis state machines) proving that production
    HashidsAdapter preserves round-trip identity invariants.
"""

from collections.abc import Sequence

from hexastack_core.ports.identity import IdObfuscatorPort

_BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE62_BASE = len(_BASE62_ALPHABET)


def _int_to_base62(num: int) -> str:
    if num == 0:
        return _BASE62_ALPHABET[0]
    chars: list[str] = []
    current = num
    while current > 0:
        current, remainder = divmod(current, _BASE62_BASE)
        chars.append(_BASE62_ALPHABET[remainder])
    chars.reverse()
    return "".join(chars)


def _base62_to_int(token: str) -> int:
    num = 0
    for char in token:
        idx = _BASE62_ALPHABET.find(char)
        if idx == -1:
            msg = f"Invalid character {char!r} in Base62 token"
            raise ValueError(msg)
        num = num * _BASE62_BASE + idx
    return num


class InMemoryIdObfuscator(IdObfuscatorPort):
    """Reference in-memory identifier obfuscator using Base62 encoding."""

    def __init__(self, min_length: int = 1, prefix: str = "") -> None:
        """Initialize InMemoryIdObfuscator.

        Args:
            min_length: Minimum generated token character length. Defaults to 1.
            prefix: Optional static string prefix for generated tokens.

        Raises:
            ValueError: If min_length is negative.
        """
        if min_length < 0:
            msg = f"min_length must be non-negative, got {min_length}"
            raise ValueError(msg)
        self._min_length = min_length
        self._prefix = prefix

    def encode(self, number: int) -> str:
        """Encode an integer into a Base62 token.

        Args:
            number: Non-negative integer to encode.

        Returns:
            Encoded string token.

        Raises:
            ValueError: If number is negative.
        """
        if number < 0:
            msg = f"Cannot encode negative integer: {number}"
            raise ValueError(msg)

        b62 = _int_to_base62(number)
        if len(b62) < self._min_length:
            b62 = b62.rjust(self._min_length, _BASE62_ALPHABET[0])
        return f"{self._prefix}{b62}"

    def decode(self, token: str) -> int:
        """Decode a Base62 token back into its original integer.

        Args:
            token: Encoded string token.

        Returns:
            Original decoded integer.

        Raises:
            ValueError: If token does not match prefix or is malformed.
        """
        if not token or not isinstance(token, str):
            msg = f"Invalid token format: {token!r}"
            raise ValueError(msg)

        if self._prefix and not token.startswith(self._prefix):
            msg = f"Token {token!r} missing expected prefix {self._prefix!r}"
            raise ValueError(msg)

        payload = token[len(self._prefix) :]
        return _base62_to_int(payload)

    def encode_many(self, numbers: Sequence[int]) -> str:
        """Encode multiple non-negative integers into a composite token.

        Args:
            numbers: Sequence of non-negative integers.

        Returns:
            Composite string token.

        Raises:
            ValueError: If sequence is empty or any integer is negative.
        """
        if not numbers:
            msg = "Cannot encode empty sequence of numbers"
            raise ValueError(msg)

        parts = [self.encode(n) for n in numbers]
        return "-".join(parts)

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

        parts = token.split("-")
        return tuple(self.decode(p) for p in parts)


__all__ = [
    "InMemoryIdObfuscator",
]
