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
