from unittest.mock import MagicMock, patch

from hexastack_auth.adapters.opa.policy import OpaPolicyAdapter
from hexastack_auth.domain.models import Identity


def test_opa_policy_adapter_allow():
    adapter = OpaPolicyAdapter(base_url="http://mock-opa:8181")
    identity = Identity(
        user_id="user_admin",
        tenant_id="tenant-1",
        roles=frozenset({"admin"}),
        permissions=frozenset({"read"}),
        claims={"org": "acme"},
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": True}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        allowed = adapter.is_authorized(
            identity,
            "v1/data/finance/approve",
            "invoice:101",
            context={"dept": "finance"},
        )
        assert allowed is True
        mock_post.assert_called_once()
        call_url, call_kwargs = mock_post.call_args
        assert call_url[0] == "http://mock-opa:8181/v1/data/finance/approve"
        payload = call_kwargs["json"]["input"]
        assert payload["identity"]["user_id"] == "user_admin"
        assert payload["identity"]["tenant_id"] == "tenant-1"
        assert payload["identity"]["is_authenticated"] is True
        assert "admin" in payload["identity"]["roles"]
        assert "read" in payload["identity"]["permissions"]
        assert payload["identity"]["claims"] == {"org": "acme"}
        assert payload["action"] == "v1/data/finance/approve"
        assert payload["resource"] == "invoice:101"
        assert payload["context"] == {"dept": "finance"}


def test_opa_policy_adapter_branches():
    adapter = OpaPolicyAdapter(
        base_url="http://mock-opa:8181",
        default_policy_path="v1/data/default/allow",
        timeout=5.0,
    )
    identity = Identity(user_id="user_guest")

    # 1. Fallback to default_policy_path when action does not start with v1/data or policies/
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"result": {"allow": True}}
    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        assert adapter.is_authorized(identity, "read", "document:1") is True
        assert mock_post.call_args[0][0] == "http://mock-opa:8181/v1/data/default/allow"

    # 2. Dict result with allow=False
    mock_resp.json.return_value = {"result": {"allow": False}}
    with patch("httpx.Client.post", return_value=mock_resp):
        assert adapter.is_authorized(identity, "read", "document:1") is False

    # 3. Non-200 HTTP status
    mock_resp.status_code = 500
    with patch("httpx.Client.post", return_value=mock_resp):
        assert adapter.is_authorized(identity, "read", "document:1") is False

    # 4. HTTP client network exception / timeout
    with patch("httpx.Client.post", side_effect=Exception("Connection refused")):
        assert adapter.is_authorized(identity, "read", "document:1") is False
