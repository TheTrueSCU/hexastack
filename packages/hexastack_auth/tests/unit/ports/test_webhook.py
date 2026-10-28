"""Unit tests verifying WebhookSignatureVerifierPort contract."""

from collections.abc import Mapping

import pytest

from hexastack_auth.ports.webhook import WebhookSignatureVerifierPort


def test_webhook_port_abstract_methods() -> None:
    """Verify WebhookSignatureVerifierPort cannot be instantiated without verify implementation."""
    with pytest.raises(TypeError):
        WebhookSignatureVerifierPort()  # ty: ignore[call-non-callable]


def test_webhook_port_concrete_subclass() -> None:
    """Verify concrete subclass can be instantiated and invoked."""

    class DummyVerifier(WebhookSignatureVerifierPort):
        def verify(
            self,
            payload: bytes,
            headers: Mapping[str, str],
            secret: str,
        ) -> bool:
            return True

    verifier = DummyVerifier()
    res = verifier.verify(b"payload", {}, "secret")
    assert res is True
