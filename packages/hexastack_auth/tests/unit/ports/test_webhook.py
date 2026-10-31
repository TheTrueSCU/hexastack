"""Unit tests verifying WebhookSignatureVerifierPort contract."""

import inspect
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


def test_webhook_signature_verifier_port_is_abstract() -> None:
    """Verify that WebhookSignatureVerifierPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(WebhookSignatureVerifierPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        WebhookSignatureVerifierPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_webhook_signature_verifier_port_abstract_methods() -> None:
    """Verify abstract methods on WebhookSignatureVerifierPort."""
    expected = {"verify"}
    abstracts = WebhookSignatureVerifierPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
