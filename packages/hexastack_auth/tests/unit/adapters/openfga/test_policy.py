from unittest.mock import MagicMock, patch

from hexastack_auth.adapters.openfga.policy import OpenFgaPolicyAdapter
from hexastack_auth.domain.models import Identity


def test_openfga_policy_adapter_allow():
    adapter = OpenFgaPolicyAdapter(
        api_url="http://mock-openfga:8080", store_id="store_xyz", model_id="model_123"
    )
    identity = Identity(user_id="alice")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"allowed": True}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        allowed = adapter.is_authorized(identity, "can_edit", "document:101")
        assert allowed is True
        mock_post.assert_called_once()
        call_url, call_kwargs = mock_post.call_args
        assert call_url[0] == "http://mock-openfga:8080/stores/store_xyz/check"
        payload = call_kwargs["json"]
        assert payload["tuple_key"]["user"] == "user:alice"
        assert payload["tuple_key"]["relation"] == "can_edit"
        assert payload["tuple_key"]["object"] == "document:101"
        assert payload["authorization_model_id"] == "model_123"


def test_openfga_policy_adapter_branches():
    adapter = OpenFgaPolicyAdapter(
        api_url="http://mock-openfga:8080", store_id="store_xyz"
    )
    identity = Identity(user_id="bob")

    # 1. Deny case
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"allowed": False}
    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        assert adapter.is_authorized(identity, "can_view", "document:102") is False
        assert mock_post.call_args[1]["json"]["tuple_key"]["user"] == "user:bob"

    # 2. Non-200 status code
    mock_resp.status_code = 500
    with patch("httpx.Client.post", return_value=mock_resp):
        assert adapter.is_authorized(identity, "can_view", "document:102") is False

    # 3. Network error / Exception
    with patch("httpx.Client.post", side_effect=Exception("OpenFGA down")):
        assert adapter.is_authorized(identity, "can_view", "document:102") is False
