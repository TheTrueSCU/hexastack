from unittest.mock import MagicMock, patch

from hexastack_auth.adapters.opa.policy import OpaPolicyAdapter
from hexastack_auth.domain.models import Identity


def test_opa_policy_adapter_allow():
    adapter = OpaPolicyAdapter(base_url="http://mock-opa:8181")
    identity = Identity(user_id="user_admin", roles=frozenset({"admin"}))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": True}

    with patch("httpx.Client.post", return_value=mock_resp):
        allowed = adapter.is_authorized(
            identity, "v1/data/finance/approve", "invoice:101"
        )
        assert allowed is True


def test_opa_policy_adapter_deny():
    adapter = OpaPolicyAdapter(base_url="http://mock-opa:8181")
    identity = Identity(user_id="user_guest")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": False}

    with patch("httpx.Client.post", return_value=mock_resp):
        allowed = adapter.is_authorized(
            identity, "v1/data/finance/approve", "invoice:101"
        )
        assert allowed is False
