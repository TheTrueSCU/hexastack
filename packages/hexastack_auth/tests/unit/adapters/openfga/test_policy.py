from unittest.mock import MagicMock, patch

from hexastack_auth.adapters.openfga.policy import OpenFgaPolicyAdapter
from hexastack_auth.domain.models import Identity


def test_openfga_policy_adapter_allow():
    adapter = OpenFgaPolicyAdapter(
        api_url="http://mock-openfga:8080", store_id="store_xyz"
    )
    identity = Identity(user_id="alice")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"allowed": True}

    with patch("httpx.Client.post", return_value=mock_resp):
        allowed = adapter.is_authorized(identity, "can_edit", "document:101")
        assert allowed is True


def test_openfga_policy_adapter_deny():
    adapter = OpenFgaPolicyAdapter(
        api_url="http://mock-openfga:8080", store_id="store_xyz"
    )
    identity = Identity(user_id="bob")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"allowed": False}

    with patch("httpx.Client.post", return_value=mock_resp):
        allowed = adapter.is_authorized(identity, "can_edit", "document:101")
        assert allowed is False
