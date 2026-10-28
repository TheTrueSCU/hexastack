"""Cryptographic webhook signature verifiers for GitHub, Stripe, Svix, and HMAC-SHA256.

Notes/Architectural Intent:
    Provides concrete implementations of WebhookSignatureVerifierPort using
    standard library hmac, hashlib, and base64 modules. Enforces constant-time
    digest comparison (hmac.compare_digest) to prevent timing-attack vulnerabilities,
    and validates timestamp tolerances to prevent replay attacks.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import time
from collections.abc import Mapping

from hexastack_auth.domain.exceptions import (
    InvalidWebhookSignatureError,
    WebhookReplayError,
)
from hexastack_auth.ports.webhook import WebhookSignatureVerifierPort

__all__ = [
    "GitHubWebhookVerifier",
    "HmacSha256Verifier",
    "StandardWebhooksVerifier",
    "StripeWebhookVerifier",
    "SvixWebhookVerifier",
]


def _get_header(headers: Mapping[str, str], header_name: str) -> str | None:
    """Case-insensitive header retrieval from a mapping.

    Args:
        headers: Mapping of HTTP request headers.
        header_name: Name of the header to search.

    Returns:
        Header string value if found, or None.
    """
    target = header_name.lower()
    for k, v in headers.items():
        if k.lower() == target:
            return v
    return None


class HmacSha256Verifier(WebhookSignatureVerifierPort):
    """Generic HMAC-SHA256 webhook signature verifier.

    Args:
        header_name: HTTP header carrying the signature (defaults to 'X-Signature-256').
        prefix: Optional prefix in header before hex digest (e.g. 'sha256=').

    Notes/Architectural Intent:
        Offers a configurable HMAC-SHA256 verification adapter for custom webhook
        transports with constant-time equality checks.
    """

    def __init__(
        self,
        header_name: str = "X-Signature-256",
        prefix: str = "sha256=",
    ) -> None:
        self.header_name = header_name
        self.prefix = prefix

    def verify(
        self,
        payload: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Verify generic HMAC-SHA256 signature against incoming payload.

        Args:
            payload: Raw unmodified bytes of incoming request body.
            headers: Mapping of incoming HTTP request headers.
            secret: Shared secret string.

        Returns:
            True if signature matches.

        Raises:
            InvalidWebhookSignatureError: If header is missing or signature does not match.
        """
        raw_sig = _get_header(headers, self.header_name)
        if raw_sig is None:
            raise InvalidWebhookSignatureError(
                f"Missing required webhook signature header '{self.header_name}'"
            )

        sig = raw_sig.strip()
        if self.prefix and sig.startswith(self.prefix):
            sig = sig[len(self.prefix) :]

        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(sig, expected):
            raise InvalidWebhookSignatureError(
                "Cryptographic webhook signature verification failed"
            )
        return True


class GitHubWebhookVerifier(WebhookSignatureVerifierPort):
    """GitHub webhook signature verifier enforcing 'X-Hub-Signature-256'.

    Notes/Architectural Intent:
        Implements GitHub's HMAC-SHA256 webhook verification specification,
        guaranteeing authenticity of incoming events (e.g. workflow_job, push).
    """

    HEADER_NAME: str = "X-Hub-Signature-256"
    PREFIX: str = "sha256="

    def verify(
        self,
        payload: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Verify GitHub HMAC-SHA256 signature.

        Args:
            payload: Raw unmodified bytes of incoming request body.
            headers: Mapping of incoming HTTP request headers.
            secret: GitHub webhook secret.

        Returns:
            True if signature matches.

        Raises:
            InvalidWebhookSignatureError: If header is missing or signature does not match.
        """
        raw_sig = _get_header(headers, self.HEADER_NAME)
        if raw_sig is None:
            raise InvalidWebhookSignatureError(
                f"Missing required GitHub webhook signature header '{self.HEADER_NAME}'"
            )

        sig = raw_sig.strip()
        if not sig.startswith(self.PREFIX):
            raise InvalidWebhookSignatureError(
                f"Malformed GitHub webhook signature; expected '{self.PREFIX}' prefix"
            )

        provided_digest = sig[len(self.PREFIX) :]
        expected_digest = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provided_digest, expected_digest):
            raise InvalidWebhookSignatureError("Invalid GitHub webhook signature")
        return True


class StripeWebhookVerifier(WebhookSignatureVerifierPort):
    """Stripe webhook signature verifier with timestamped replay tolerance.

    Args:
        tolerance_seconds: Maximum allowable age/drift of webhook timestamp in seconds (defaults to 300).

    Notes/Architectural Intent:
        Implements Stripe's 'Stripe-Signature' format (t=<timestamp>,v1=<signature>),
        verifying that timestamp + '.' + payload matches v1 and that the event is within tolerance.
    """

    HEADER_NAME: str = "Stripe-Signature"

    def __init__(self, tolerance_seconds: int = 300) -> None:
        self.tolerance_seconds = tolerance_seconds

    def verify(
        self,
        payload: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Verify Stripe webhook signature and timestamp freshness.

        Args:
            payload: Raw unmodified bytes of incoming request body.
            headers: Mapping of incoming HTTP request headers.
            secret: Stripe webhook endpoint secret (typically 'whsec_...').

        Returns:
            True if at least one v1 signature matches and timestamp is within tolerance.

        Raises:
            InvalidWebhookSignatureError: If header is missing or signatures do not match.
            WebhookReplayError: If timestamp is outside allowable tolerance.
        """
        raw_sig = _get_header(headers, self.HEADER_NAME)
        if raw_sig is None:
            raise InvalidWebhookSignatureError(
                f"Missing required Stripe webhook signature header '{self.HEADER_NAME}'"
            )

        timestamp: int | None = None
        v1_signatures: list[str] = []

        for item in raw_sig.split(","):
            parts = item.strip().split("=", 1)
            if len(parts) == 2:
                key, val = parts[0].strip(), parts[1].strip()
                if key == "t":
                    with contextlib.suppress(ValueError):
                        timestamp = int(val)
                elif key == "v1":
                    v1_signatures.append(val)

        if timestamp is None or not v1_signatures:
            raise InvalidWebhookSignatureError(
                "Malformed 'Stripe-Signature' header: missing timestamp 't' or 'v1' signatures"
            )

        if self.tolerance_seconds > 0:
            current_time = int(time.time())
            if abs(current_time - timestamp) > self.tolerance_seconds:
                raise WebhookReplayError(
                    f"Stripe webhook timestamp {timestamp} exceeds tolerance of {self.tolerance_seconds}s"
                )

        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        matched = any(hmac.compare_digest(v1_sig, expected) for v1_sig in v1_signatures)
        if not matched:
            raise InvalidWebhookSignatureError("No matching Stripe v1 signature found")
        return True


class SvixWebhookVerifier(WebhookSignatureVerifierPort):
    """Svix and Standard Webhooks specification signature verifier.

    Args:
        tolerance_seconds: Maximum allowable age/drift of webhook timestamp in seconds (defaults to 300).

    Notes/Architectural Intent:
        Implements Standard Webhooks spec (webhook-id, webhook-timestamp, webhook-signature),
        also accepting legacy 'svix-*' headers for seamless interoperability.
    """

    def __init__(self, tolerance_seconds: int = 300) -> None:
        self.tolerance_seconds = tolerance_seconds

    def _resolve_header(
        self,
        headers: Mapping[str, str],
        standard_name: str,
        legacy_name: str,
    ) -> str | None:
        val = _get_header(headers, standard_name)
        if val is None:
            val = _get_header(headers, legacy_name)
        return val

    def verify(
        self,
        payload: bytes,
        headers: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Verify Svix / Standard Webhooks signature and timestamp freshness.

        Args:
            payload: Raw unmodified bytes of incoming request body.
            headers: Mapping of incoming HTTP request headers.
            secret: Webhook signing secret (base64 or 'whsec_' prefixed).

        Returns:
            True if a v1 signature matches and timestamp is within tolerance.

        Raises:
            InvalidWebhookSignatureError: If headers are missing or signatures do not match.
            WebhookReplayError: If timestamp is outside allowable tolerance.
        """
        msg_id = self._resolve_header(headers, "webhook-id", "svix-id")
        timestamp_str = self._resolve_header(
            headers, "webhook-timestamp", "svix-timestamp"
        )
        sig_header = self._resolve_header(
            headers, "webhook-signature", "svix-signature"
        )

        if not msg_id or not timestamp_str or not sig_header:
            raise InvalidWebhookSignatureError(
                "Missing required Svix/Standard-Webhooks headers (id, timestamp, or signature)"
            )

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise InvalidWebhookSignatureError(
                f"Invalid Svix webhook timestamp value: '{timestamp_str}'"
            ) from None

        if self.tolerance_seconds > 0:
            current_time = int(time.time())
            if abs(current_time - timestamp) > self.tolerance_seconds:
                raise WebhookReplayError(
                    f"Svix webhook timestamp {timestamp} exceeds tolerance of {self.tolerance_seconds}s"
                )

        key: bytes
        raw_secret = secret.strip()
        if raw_secret.startswith("whsec_"):
            raw_secret = raw_secret[len("whsec_") :]
            try:
                key = base64.b64decode(raw_secret)
            except Exception as exc:
                raise InvalidWebhookSignatureError(
                    "Invalid base64 encoding in 'whsec_' secret"
                ) from exc
        else:
            try:
                key = base64.b64decode(raw_secret)
            except Exception:
                key = raw_secret.encode("utf-8")

        signed_payload = f"{msg_id}.{timestamp_str}.".encode() + payload
        expected_digest = base64.b64encode(
            hmac.new(key, signed_payload, hashlib.sha256).digest()
        ).decode("utf-8")

        v1_signatures: list[str] = []
        for token in sig_header.strip().split():
            parts = token.split(",", 1)
            if len(parts) == 2 and parts[0] == "v1":
                v1_signatures.append(parts[1])

        matched = any(
            hmac.compare_digest(v1_sig, expected_digest) for v1_sig in v1_signatures
        )
        if not matched:
            raise InvalidWebhookSignatureError(
                "No matching Svix/Standard-Webhooks v1 signature found"
            )
        return True


StandardWebhooksVerifier = SvixWebhookVerifier
