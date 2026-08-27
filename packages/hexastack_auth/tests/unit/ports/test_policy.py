"""Unit tests for authorization policy ports."""

from hexastack_auth.ports.policy import AuthorizationPolicyPort


def test_authorization_policy_port_interface() -> None:
    assert hasattr(AuthorizationPolicyPort, "is_authorized")


def test_authorization_policy_port_protocol_default_callables() -> None:
    from typing import Any

    dummy: Any = None
    AuthorizationPolicyPort.is_authorized(dummy, dummy, "read", "res")


def test_workload_identity_port_protocol_default_callables() -> None:
    from typing import Any

    from hexastack_auth.ports.workload import WorkloadIdentityPort

    dummy: Any = None
    WorkloadIdentityPort.fetch_jwt_svid(dummy, {"aud"})
    WorkloadIdentityPort.get_spiffe_id(dummy)
    WorkloadIdentityPort.validate_jwt_svid(dummy, "tok", {"aud"})
