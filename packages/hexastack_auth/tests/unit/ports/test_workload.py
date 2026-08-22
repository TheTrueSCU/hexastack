"""Unit tests for workload identity ports."""

from hexastack_auth.ports.workload import WorkloadIdentityPort


def test_workload_identity_port_interface() -> None:
    assert hasattr(WorkloadIdentityPort, "fetch_jwt_svid")
    assert hasattr(WorkloadIdentityPort, "get_spiffe_id")
    assert hasattr(WorkloadIdentityPort, "validate_jwt_svid")
