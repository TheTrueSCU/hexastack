from unittest.mock import MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_auth.adapters.fastapi import require_policy, require_relation
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_core.utils.context import (
    UserContext,
    correlation_scope,
    set_user_context,
)


def test_fastapi_require_policy_guard():
    policy_mock = MagicMock()
    # Allow when user is admin, deny otherwise
    policy_mock.is_authorized.side_effect = lambda identity, action, resource, context: (
        "admin" in identity.roles
    )

    app = FastAPI()
    container = Container()
    container.add_instance(policy_mock, declared_class=AuthorizationPolicyPort)
    app.state.container = container

    @app.get("/secret", dependencies=[Depends(require_policy("v1/data/secret/view"))])
    def get_secret():
        return {"secret": "42"}

    client = TestClient(app)

    # 1. Denied when guest
    with correlation_scope("test-1"):
        set_user_context(UserContext(user_id="guest", roles=[]))
        res = client.get("/secret")
        assert res.status_code == 403

    # 2. Allowed when admin
    with correlation_scope("test-2"):
        set_user_context(UserContext(user_id="alice", roles=["admin"]))
        res = client.get("/secret")
        assert res.status_code == 200
        assert res.json() == {"secret": "42"}


def test_fastapi_require_relation_guard():
    policy_mock = MagicMock()
    policy_mock.is_authorized.return_value = True

    app = FastAPI()
    container = Container()
    container.add_instance(policy_mock, declared_class=AuthorizationPolicyPort)
    app.state.container = container

    @app.get(
        "/docs/{doc_id}",
        dependencies=[Depends(require_relation("editor", "document", "101"))],
    )
    def edit_doc(doc_id: str):
        return {"status": "edited", "id": doc_id}

    client = TestClient(app)
    with correlation_scope("test-3"):
        set_user_context(UserContext(user_id="editor_user", roles=[]))
        res = client.get("/docs/101")
        assert res.status_code == 200
        assert res.json() == {"status": "edited", "id": "101"}


def test_fastapi_require_policy_missing_container_or_port_raises_500():
    """Verify require_policy raises HTTP 500 when container or AuthorizationPolicyPort is absent."""
    app = FastAPI()

    @app.get("/guarded", dependencies=[Depends(require_policy("v1/data/test"))])
    def guarded_endpoint():
        return {"ok": True}

    client = TestClient(app)
    # 1. No container configured on app.state
    res = client.get("/guarded")
    assert res.status_code == 500
    assert "AuthorizationPolicyPort is not configured" in res.json()["detail"]

    # 2. Container configured on app.state, but AuthorizationPolicyPort is missing
    app.state.container = Container()
    res2 = client.get("/guarded")
    assert res2.status_code == 500
    assert "AuthorizationPolicyPort is not configured" in res2.json()["detail"]


def test_fastapi_require_relation_missing_container_or_port_raises_500():
    """Verify require_relation raises HTTP 500 when container or AuthorizationPolicyPort is absent."""
    app = FastAPI()

    @app.get(
        "/guarded-relation",
        dependencies=[Depends(require_relation("editor", "doc", "1"))],
    )
    def guarded_relation():
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/guarded-relation")
    assert res.status_code == 500
    assert "AuthorizationPolicyPort is not configured" in res.json()["detail"]


def test_fastapi_require_policy_anonymous_and_custom_errors():
    """Verify anonymous user fallback and customized status code/detail."""
    policy_mock = MagicMock()
    # Allow only authenticated users
    policy_mock.is_authorized.side_effect = lambda identity, action, resource, context: (
        identity.is_authenticated and identity.user_id != "anonymous"
    )

    app = FastAPI()
    container = Container()
    container.add_instance(policy_mock, declared_class=AuthorizationPolicyPort)
    app.state.container = container

    @app.get(
        "/custom-guard",
        dependencies=[
            Depends(
                require_policy(
                    "v1/data/report",
                    resource="reports",
                    status_code=401,
                    detail="Please sign in to access reports.",
                )
            )
        ],
    )
    def custom_endpoint():
        return {"data": "report"}

    client = TestClient(app)

    # 1. Unset user context (defaults to anonymous)
    set_user_context(None)
    res = client.get("/custom-guard")
    assert res.status_code == 401
    assert res.json()["detail"] == "Please sign in to access reports."

    # 2. Empty user_id in user context (defaults to anonymous / is_authenticated=False)
    set_user_context(UserContext(user_id="", roles=[]))
    res2 = client.get("/custom-guard")
    assert res2.status_code == 401


def test_fastapi_require_relation_custom_status_code_and_detail():
    """Verify custom error detail and status codes in require_relation."""
    policy_mock = MagicMock()
    policy_mock.is_authorized.return_value = False

    app = FastAPI()
    container = Container()
    container.add_instance(policy_mock, declared_class=AuthorizationPolicyPort)
    app.state.container = container

    @app.get(
        "/workspace/{ws_id}",
        dependencies=[
            Depends(
                require_relation(
                    "admin",
                    "workspace",
                    status_code=404,
                    detail="Workspace not found or access denied.",
                )
            )
        ],
    )
    def get_workspace(ws_id: str):
        return {"id": ws_id}

    client = TestClient(app)
    set_user_context(UserContext(user_id="bob", roles=[]))
    res = client.get("/workspace/ws-99")
    assert res.status_code == 404
    assert res.json()["detail"] == "Workspace not found or access denied."
