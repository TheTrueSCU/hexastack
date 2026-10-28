from unittest.mock import AsyncMock, MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_auth.adapters.fastapi import (
    create_auth_router,
    create_oauth_router,
    require_policy,
    require_relation,
)
from hexastack_auth.adapters.handlers import UserLifecycleHandlers
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.oauth import GoogleOAuthProvider
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.adapters.user_repository import (
    InMemoryTokenStore,
    InMemoryUserRepository,
)
from hexastack_auth.domain.exceptions import OAuthProviderError
from hexastack_auth.domain.user import OAuthUserInfo
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


def test_create_auth_router_complete_lifecycle():
    user_repo = InMemoryUserRepository()
    token_store = InMemoryTokenStore()
    hasher = Pbkdf2PasswordHasher(iterations=10_000)
    handlers = UserLifecycleHandlers(
        user_repository=user_repo,
        token_store=token_store,
        password_hasher=hasher,
    )
    jwt_adapter = JwtSecurityAdapter(secret_key="unit-test-secret-key-32-bytes-long!")

    router = create_auth_router(
        handlers=handlers,
        jwt_adapter=jwt_adapter,
        cookie_name="test_session",
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # 1. Register new user
    reg_payload = {
        "email": "user@example.com",
        "password": "Password123!",  # pragma: allowlist secret
    }
    res_reg = client.post("/auth/register", json=reg_payload)
    assert res_reg.status_code == 201
    user_data = res_reg.json()
    assert user_data["email"] == "user@example.com"
    assert user_data["is_verified"] is False
    assert user_data["is_active"] is True

    # 2. Duplicate registration -> 409 Conflict
    res_dup = client.post("/auth/register", json=reg_payload)
    assert res_dup.status_code == 409

    # 3. Invalid payload (password < 8 chars) -> 422
    res_invalid_req = client.post(
        "/auth/register",
        json={
            "email": "bad@example.com",
            "password": "short",  # pragma: allowlist secret
        },
    )
    assert res_invalid_req.status_code == 422

    # 4. Login -> 200 with JWT and Cookie
    login_payload = {
        "email": "user@example.com",
        "password": "Password123!",  # pragma: allowlist secret
    }
    res_login = client.post("/auth/login", json=login_payload)
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert "test_session" in res_login.cookies

    # 5. Login with invalid password -> 401
    bad_login = {
        "email": "user@example.com",
        "password": "WrongPassword!",  # pragma: allowlist secret
    }
    res_bad_login = client.post("/auth/login", json=bad_login)
    assert res_bad_login.status_code == 401

    # 6. Verify email
    # Extract verification token directly from token_store for deterministic test
    token_obj = next(iter(token_store._tokens.values()))
    res_verify = client.post("/auth/verify", json={"token": token_obj.token})
    assert res_verify.status_code == 200
    verified_data = res_verify.json()
    assert verified_data["is_verified"] is True

    # 7. Verify with invalid token -> 400
    res_bad_verify = client.post(
        "/auth/verify", json={"token": "invalid_or_consumed_token"}
    )
    assert res_bad_verify.status_code == 400

    # 8. Forgot password -> 200
    res_forgot = client.post(
        "/auth/forgot-password", json={"email": "user@example.com"}
    )
    assert res_forgot.status_code == 200
    assert res_forgot.json()["status"] == "ok"

    # 9. Reset password
    reset_token_obj = next(
        t for t in token_store._tokens.values() if t.token_type == "password_reset"
    )
    res_reset = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token_obj.token,
            "new_password": "NewSecretPassword123!",  # pragma: allowlist secret
        },
    )
    assert res_reset.status_code == 200

    # 10. Login with new password
    res_new_login = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "NewSecretPassword123!",  # pragma: allowlist secret
        },
    )
    assert res_new_login.status_code == 200

    # 11. Inactive account -> 403 Forbidden
    persisted = user_repo.get_by_email("user@example.com")
    assert persisted is not None
    persisted.is_active = False
    user_repo.save(persisted)

    res_inactive = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "NewSecretPassword123!",  # pragma: allowlist secret
        },
    )
    assert res_inactive.status_code == 403


def test_create_oauth_router_flow():
    user_repo = InMemoryUserRepository()
    token_store = InMemoryTokenStore()
    handlers = UserLifecycleHandlers(user_repository=user_repo, token_store=token_store)
    jwt_adapter = JwtSecurityAdapter(secret_key="unit-test-secret-key-32-bytes-long!")

    provider = GoogleOAuthProvider(
        client_id="mock_client_id",
        client_secret="mock_client_secret",  # pragma: allowlist secret
    )

    router = create_oauth_router(
        oauth_provider=provider,
        handlers=handlers,
        jwt_adapter=jwt_adapter,
        redirect_uri="http://localhost:8000/auth/oauth/callback",
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, follow_redirects=False)

    # 1. Authorize redirect
    res_auth = client.get("/auth/oauth/google/authorize")
    assert res_auth.status_code == 307
    location = res_auth.headers.get("location", "")
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=mock_client_id" in location

    # 2. Callback success
    mock_user_info = OAuthUserInfo(
        provider="google",
        account_id="google-sub-42",
        email="oauth_dev@example.com",
        name="OAuth Dev",
    )
    provider.exchange_code = AsyncMock(return_value=mock_user_info)  # type: ignore[method-assign]

    res_callback = client.get("/auth/oauth/google/callback?code=valid_code&state=xyz")
    assert res_callback.status_code == 200
    token_data = res_callback.json()
    assert "access_token" in token_data

    # Verify user was created in repository
    user = user_repo.get_by_email("oauth_dev@example.com")
    assert user is not None
    assert user.is_verified is True
    assert len(user.oauth_accounts) == 1

    # 3. Callback error from OAuth provider
    provider.exchange_code = AsyncMock(
        side_effect=OAuthProviderError("google", "Token exchange error")
    )  # type: ignore[method-assign]
    res_err = client.get("/auth/oauth/google/callback?code=bad_code")
    assert res_err.status_code == 400
    assert "Token exchange error" in res_err.json()["detail"]
