"""Unit tests for authorization policy ports."""

from hexastack_auth.ports.policy import AuthorizationPolicyPort


def test_authorization_policy_port_interface() -> None:
    assert hasattr(AuthorizationPolicyPort, "is_authorized")
