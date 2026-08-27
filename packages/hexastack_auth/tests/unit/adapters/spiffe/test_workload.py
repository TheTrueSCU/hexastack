from hexastack_auth.adapters.spiffe.workload import SpiffeWorkloadAdapter


def test_spiffe_workload_adapter():
    adapter = SpiffeWorkloadAdapter(trust_domain="example.org")
    spiffe_id = adapter.get_spiffe_id()
    assert spiffe_id == "spiffe://example.org/workload/default"

    validated = adapter.validate_jwt_svid("dummy-token", audience={"order-service"})
    assert validated == "spiffe://example.org/caller"


def test_spiffe_workload_adapter_errors_and_fetch():
    """Verify missing dependency error on fetch_jwt_svid and validation on empty token."""
    from unittest.mock import patch

    import pytest

    from hexastack_auth.domain.exceptions import InvalidCredentialsError
    from hexastack_core.domain.exceptions import MissingDependencyError

    adapter = SpiffeWorkloadAdapter(trust_domain="custom.org")

    # 1. Normal fetch when spiffe is installed
    token = adapter.fetch_jwt_svid(audience={"svc"})
    assert token == "dummy-jwt-svid"

    # 2. When spiffe is not found
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError),
    ):
        adapter.fetch_jwt_svid(audience={"svc"})

    # 3. Empty token validation
    with pytest.raises(InvalidCredentialsError):
        adapter.validate_jwt_svid("", audience={"svc"})
