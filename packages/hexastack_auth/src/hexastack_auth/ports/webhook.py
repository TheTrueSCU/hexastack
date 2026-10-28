"""Abstract webhook signature verification port interface.

Notes/Architectural Intent:
    Decouples inbound webhook signature validation from specific web frameworks
    and third-party provider signature schemes (GitHub, Stripe, Svix, HMAC-SHA256).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

__all__ = [
    "WebhookSignatureVerifierPort",
]


class WebhookSignatureVerifierPort(ABC):
    """Abstract port interface for validating inbound cryptographic webhook signatures.

    Notes/Architectural Intent:
        Standardizes webhook authentication across providers, ensuring callers
        verify raw payload signatures before deserialization without leaking vendor
        mechanics into domain handlers.
    """

    @abstractmethod
    def verify(
        self,
        payload: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Verify that the raw payload matches the cryptographic signature in headers.

        Args:
            payload: Raw unmodified bytes of the incoming request body.
            headers: Mapping of incoming HTTP request headers (case-insensitive lookup expected).
            secret: Shared secret or webhook signing key.

        Returns:
            True if the signature is cryptographically valid.

        Raises:
            InvalidWebhookSignatureError: If the signature header is missing or cryptographically invalid.
            WebhookReplayError: If the signed timestamp exceeds allowable tolerance.
        """
