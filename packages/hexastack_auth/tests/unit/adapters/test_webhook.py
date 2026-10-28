"""Unit tests for cryptographic webhook verifiers (HMAC-SHA256, GitHub, Stripe, Svix)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import pytest

from hexastack_auth.adapters.webhook import (
    GitHubWebhookVerifier,
    HmacSha256Verifier,
    StandardWebhooksVerifier,
    StripeWebhookVerifier,
    SvixWebhookVerifier,
)
from hexastack_auth.domain.exceptions import (
    InvalidWebhookSignatureError,
    WebhookReplayError,
)


def test_hmac_sha256_verifier_success() -> None:
    """Verify generic HMAC-SHA256 verification succeeds with correct digest."""
    secret = "test-secret-key"  # pragma: allowlist secret
    payload = b'{"event":"test","status":"ok"}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    verifier = HmacSha256Verifier(header_name="X-Signature-256", prefix="sha256=")
    headers = {"X-Signature-256": f"sha256={expected}"}

    res = verifier.verify(payload, headers, secret)
    assert res is True


def test_hmac_sha256_verifier_case_insensitive_header() -> None:
    """Verify header lookup is case-insensitive."""
    secret = "test-secret-key"  # pragma: allowlist secret
    payload = b"test payload"
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    verifier = HmacSha256Verifier(header_name="X-Signature-256", prefix="")
    headers = {"x-signature-256": expected}

    res = verifier.verify(payload, headers, secret)
    assert res is True


def test_hmac_sha256_verifier_missing_header() -> None:
    """Verify Missing header raises InvalidWebhookSignatureError."""
    verifier = HmacSha256Verifier()
    with pytest.raises(
        InvalidWebhookSignatureError, match="Missing required webhook signature"
    ):
        verifier.verify(b"payload", {}, "secret")


def test_hmac_sha256_verifier_invalid_signature() -> None:
    """Verify mismatched digest raises InvalidWebhookSignatureError."""
    verifier = HmacSha256Verifier()
    headers = {"X-Signature-256": "sha256=invalidhexdigest1234567890"}
    with pytest.raises(
        InvalidWebhookSignatureError, match="signature verification failed"
    ):
        verifier.verify(b"payload", headers, "secret")


def test_github_webhook_verifier_success() -> None:
    """Verify GitHub webhook verification succeeds with X-Hub-Signature-256."""
    secret = "gh_secret_456"  # pragma: allowlist secret
    payload = b'{"action":"completed","workflow_job":{"id":123}}'
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    verifier = GitHubWebhookVerifier()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}

    res = verifier.verify(payload, headers, secret)
    assert res is True


def test_github_webhook_verifier_missing_header() -> None:
    """Verify missing GitHub signature header raises InvalidWebhookSignatureError."""
    verifier = GitHubWebhookVerifier()
    with pytest.raises(InvalidWebhookSignatureError, match="Missing required GitHub"):
        verifier.verify(b"payload", {}, "secret")


def test_github_webhook_verifier_malformed_header() -> None:
    """Verify missing sha256= prefix raises InvalidWebhookSignatureError."""
    verifier = GitHubWebhookVerifier()
    headers = {"X-Hub-Signature-256": "1234567890abcdef"}  # pragma: allowlist secret
    with pytest.raises(
        InvalidWebhookSignatureError, match="Malformed GitHub webhook signature"
    ):
        verifier.verify(b"payload", headers, "secret")


def test_github_webhook_verifier_invalid_signature() -> None:
    """Verify mismatched GitHub signature raises InvalidWebhookSignatureError."""
    verifier = GitHubWebhookVerifier()
    headers = {
        "x-hub-signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"
    }
    with pytest.raises(
        InvalidWebhookSignatureError, match="Invalid GitHub webhook signature"
    ):
        verifier.verify(b"payload", headers, "secret")


def test_stripe_webhook_verifier_success() -> None:
    """Verify Stripe webhook signature verification with valid timestamp."""
    secret = "whsec_stripe_test"  # pragma: allowlist secret
    payload = b'{"id":"evt_123","object":"event"}'
    ts = int(time.time())
    signed_payload = f"{ts}.".encode() + payload
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    verifier = StripeWebhookVerifier(tolerance_seconds=300)
    headers = {"Stripe-Signature": f"t={ts},v1={digest},v0=old_sig"}

    res = verifier.verify(payload, headers, secret)
    assert res is True


def test_stripe_webhook_verifier_replay_attack() -> None:
    """Verify Stripe webhook timestamp older than tolerance raises WebhookReplayError."""
    secret = "whsec_stripe_test"  # pragma: allowlist secret
    payload = b"payload"
    expired_ts = int(time.time()) - 600
    signed_payload = f"{expired_ts}.".encode() + payload
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    verifier = StripeWebhookVerifier(tolerance_seconds=300)
    headers = {"Stripe-Signature": f"t={expired_ts},v1={digest}"}

    with pytest.raises(WebhookReplayError, match="exceeds tolerance"):
        verifier.verify(payload, headers, secret)


def test_stripe_webhook_verifier_missing_header() -> None:
    """Verify missing Stripe-Signature raises InvalidWebhookSignatureError."""
    verifier = StripeWebhookVerifier()
    with pytest.raises(InvalidWebhookSignatureError, match="Missing required Stripe"):
        verifier.verify(b"payload", {}, "secret")


def test_stripe_webhook_verifier_malformed_header() -> None:
    """Verify malformed Stripe header raises InvalidWebhookSignatureError."""
    verifier = StripeWebhookVerifier()
    with pytest.raises(
        InvalidWebhookSignatureError, match="Malformed 'Stripe-Signature'"
    ):
        verifier.verify(b"payload", {"Stripe-Signature": "invalid_format"}, "secret")


def test_stripe_webhook_verifier_mismatched_signature() -> None:
    """Verify invalid signature raises InvalidWebhookSignatureError."""
    secret = "whsec_stripe_test"  # pragma: allowlist secret
    payload = b"payload"
    ts = int(time.time())

    verifier = StripeWebhookVerifier(tolerance_seconds=300)
    headers = {
        "Stripe-Signature": f"t={ts},v1=0000000000000000000000000000000000000000000000000000000000000000"
    }

    with pytest.raises(InvalidWebhookSignatureError, match="No matching Stripe v1"):
        verifier.verify(payload, headers, secret)


def test_svix_webhook_verifier_success() -> None:
    """Verify Svix / Standard Webhooks verification with whsec_ secret."""
    raw_key = b"sixteen_byte_key"
    secret = f"whsec_{base64.b64encode(raw_key).decode()}"  # pragma: allowlist secret
    payload = b'{"type":"invoice.paid","data":{"id":"inv_1"}}'
    msg_id = "msg_p5jXN8AQM9LqvYMoonQNZ2Bp"
    ts = str(int(time.time()))

    signed_payload = f"{msg_id}.{ts}.".encode() + payload
    digest = base64.b64encode(
        hmac.new(raw_key, signed_payload, hashlib.sha256).digest()
    ).decode()

    verifier = SvixWebhookVerifier(tolerance_seconds=300)
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": ts,
        "webhook-signature": f"v1,{digest} v1,other_sig",
    }

    res = verifier.verify(payload, headers, secret)
    assert res is True
    assert StandardWebhooksVerifier is SvixWebhookVerifier


def test_svix_webhook_verifier_legacy_headers() -> None:
    """Verify Svix verifier accepts legacy svix-* headers."""
    raw_key = b"sixteen_byte_key"
    secret = f"whsec_{base64.b64encode(raw_key).decode()}"  # pragma: allowlist secret
    payload = b"payload"
    msg_id = "msg_legacy"
    ts = str(int(time.time()))

    signed_payload = f"{msg_id}.{ts}.".encode() + payload
    digest = base64.b64encode(
        hmac.new(raw_key, signed_payload, hashlib.sha256).digest()
    ).decode()

    verifier = SvixWebhookVerifier()
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": ts,
        "svix-signature": f"v1,{digest}",
    }

    res = verifier.verify(payload, headers, secret)
    assert res is True


def test_svix_webhook_verifier_replay_attack() -> None:
    """Verify expired Svix timestamp raises WebhookReplayError."""
    raw_key = b"sixteen_byte_key"
    secret = f"whsec_{base64.b64encode(raw_key).decode()}"  # pragma: allowlist secret
    payload = b"payload"
    msg_id = "msg_1"
    expired_ts = str(int(time.time()) - 600)

    signed_payload = f"{msg_id}.{expired_ts}.".encode() + payload
    digest = base64.b64encode(
        hmac.new(raw_key, signed_payload, hashlib.sha256).digest()
    ).decode()

    verifier = SvixWebhookVerifier(tolerance_seconds=300)
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": expired_ts,
        "webhook-signature": f"v1,{digest}",
    }

    with pytest.raises(WebhookReplayError, match="exceeds tolerance"):
        verifier.verify(payload, headers, secret)


def test_svix_webhook_verifier_missing_headers() -> None:
    """Verify missing required Svix headers raises InvalidWebhookSignatureError."""
    verifier = SvixWebhookVerifier()
    with pytest.raises(InvalidWebhookSignatureError, match="Missing required Svix"):
        verifier.verify(b"payload", {"webhook-id": "1"}, "whsec_key")


def test_svix_webhook_verifier_mismatched_signature() -> None:
    """Verify invalid Svix signature raises InvalidWebhookSignatureError."""
    raw_key = b"sixteen_byte_key"
    secret = f"whsec_{base64.b64encode(raw_key).decode()}"  # pragma: allowlist secret
    verifier = SvixWebhookVerifier()
    headers = {
        "webhook-id": "msg_1",
        "webhook-timestamp": str(int(time.time())),
        "webhook-signature": "v1,aW52YWxpZHNpZw==",
    }
    with pytest.raises(InvalidWebhookSignatureError, match="No matching Svix"):
        verifier.verify(b"payload", headers, secret)
