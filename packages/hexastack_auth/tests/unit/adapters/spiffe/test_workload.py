from hexastack_auth.adapters.spiffe.workload import SpiffeWorkloadAdapter


def test_spiffe_workload_adapter():
    adapter = SpiffeWorkloadAdapter(trust_domain="example.org")
    spiffe_id = adapter.get_spiffe_id()
    assert spiffe_id == "spiffe://example.org/workload/default"

    validated = adapter.validate_jwt_svid("dummy-token", audience={"order-service"})
    assert validated == "spiffe://example.org/caller"
