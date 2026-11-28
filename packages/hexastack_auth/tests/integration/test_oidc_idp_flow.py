"""Hermetic self-hosted loopback OIDC Identity Provider integration tests."""

import json
import threading
import urllib.parse
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Annotated, Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from hexastack_auth.adapters.fastapi import (
    create_oauth_router,
    require_bearer_token,
)
from hexastack_auth.adapters.handlers import UserLifecycleHandlers
from hexastack_auth.adapters.oauth import GenericOidcProvider
from hexastack_auth.adapters.oidc import JwksOidcSecurityAdapter
from hexastack_auth.adapters.user_repository import (
    InMemoryTokenStore,
    InMemoryUserRepository,
)
from hexastack_auth.domain.exceptions import OAuthProviderError
from hexastack_auth.domain.models import Identity
from hexastack_auth.domain.oidc import verify_pkce_s256


@dataclass
class _AuthCodeRecord:
    client_id: str
    redirect_uri: str
    code_challenge: str
    nonce: str | None


@dataclass
class _LoopbackOidcState:
    issuer: str
    keys: dict[str, rsa.RSAPrivateKey] = field(default_factory=dict)
    active_kid: str = "kid-1"
    published_kids: list[str] = field(default_factory=lambda: ["kid-1"])
    codes: dict[str, _AuthCodeRecord] = field(default_factory=dict)
    code_seq: int = 0

    def rotate_key(self) -> None:
        self.active_kid = "kid-2"
        if "kid-2" not in self.published_kids:
            self.published_kids.append("kid-2")

    def jwks_payload(self) -> dict[str, Any]:
        keys: list[dict[str, Any]] = []
        for kid in self.published_kids:
            jwk_dict = RSAAlgorithm.to_jwk(self.keys[kid].public_key(), as_dict=True)
            jwk_dict.update({"kid": kid, "use": "sig", "alg": "RS256"})
            keys.append(jwk_dict)
        return {"keys": keys}

    def mint_access_token(
        self,
        *,
        aud: str = "hexastack-api",
        iss: str | None = None,
        offset_seconds: int = 300,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": "oidc-alice",
            "iss": iss or self.issuer,
            "aud": aud,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=offset_seconds)).timestamp()),
            "roles": ["admin", "developer"],
            "permissions": ["workflows:run", "secrets:read"],
            "tenant_id": "org-hexastack",
        }
        return jwt.encode(
            payload,
            self.keys[self.active_kid],
            algorithm="RS256",
            headers={"kid": self.active_kid, "typ": "at+jwt"},
        )

    def mint_id_token(self, *, client_id: str, nonce: str | None) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": "oidc-alice",
            "iss": self.issuer,
            "aud": client_id,
            "token_use": "id",
            "email": "alice@hexastack.dev",
            "name": "Alice OIDC",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
        if nonce is not None:
            payload["nonce"] = nonce
        return jwt.encode(
            payload,
            self.keys[self.active_kid],
            algorithm="RS256",
            headers={"kid": self.active_kid, "typ": "id+jwt"},
        )


_ALLOWED_REDIRECT_URIS: dict[str, str] = {
    "http://testserver/auth/oauth/oidc/callback": "http://testserver/auth/oauth/oidc/callback",
    "http://127.0.0.1/cb": "http://127.0.0.1/cb",
}


def _make_idp_handler(state: _LoopbackOidcState) -> type[BaseHTTPRequestHandler]:
    class _OidcHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            """Silence default BaseHTTPRequestHandler stderr logging."""
            return

        def _send_json(self, status_code: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/.well-known/openid-configuration":
                self._send_json(
                    200,
                    {
                        "issuer": state.issuer,
                        "authorization_endpoint": f"{state.issuer}/authorize",
                        "token_endpoint": f"{state.issuer}/token",
                        "userinfo_endpoint": f"{state.issuer}/userinfo",
                        "jwks_uri": f"{state.issuer}/jwks.json",
                        "id_token_signing_alg_values_supported": ["RS256"],
                        "code_challenge_methods_supported": ["S256"],
                    },
                )
                return
            if parsed.path == "/jwks.json":
                self._send_json(200, state.jwks_payload())
                return
            if parsed.path == "/authorize":
                self._handle_authorize(parsed.query)
                return
            if parsed.path == "/userinfo":
                self._handle_userinfo()
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/token":
                self._handle_token()
                return
            self._send_json(404, {"error": "not_found"})

        def _handle_authorize(self, query: str) -> None:
            params = urllib.parse.parse_qs(query)
            method = params.get("code_challenge_method", [""])[0]
            challenge = params.get("code_challenge", [""])[0]
            redirect_uri = params.get("redirect_uri", [""])[0]
            safe_redirect = _ALLOWED_REDIRECT_URIS.get(redirect_uri)
            oauth_state = params.get("state", [""])[0]
            client_id = params.get("client_id", [""])[0]
            nonce = params.get("nonce", [None])[0]
            if safe_redirect is None or method != "S256" or not challenge:
                self._send_json(400, {"error": "pkce_s256_required"})
                return
            state.code_seq += 1
            code = f"auth-code-{state.code_seq}"
            state.codes[code] = _AuthCodeRecord(
                client_id=client_id,
                redirect_uri=safe_redirect,
                code_challenge=challenge,
                nonce=nonce,
            )
            sep = "&" if "?" in safe_redirect else "?"
            raw_location = f"{safe_redirect}{sep}" + urllib.parse.urlencode(
                {"code": code, "state": oauth_state}
            )
            clean_location = raw_location.replace("\r", "").replace("\n", "")
            self.send_response(302)
            self.send_header("Location", clean_location)
            self.end_headers()

        def _handle_userinfo(self) -> None:
            auth = self.headers.get("Authorization", "")
            token = auth.removeprefix("Bearer ").strip()
            for kid in state.published_kids:
                try:
                    jwt.decode(
                        token,
                        state.keys[kid].public_key(),
                        algorithms=["RS256"],
                        audience="hexastack-api",
                        issuer=state.issuer,
                    )
                    self._send_json(
                        200,
                        {
                            "sub": "oidc-alice",
                            "email": "alice@hexastack.dev",
                            "name": "Alice OIDC",
                        },
                    )
                    return
                except jwt.PyJWTError:
                    continue
            self._send_json(401, {"error": "invalid_token"})

        def _handle_token(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            form = urllib.parse.parse_qs(raw_body)
            code = form.get("code", [""])[0]
            code_verifier = form.get("code_verifier", [""])[0]
            redirect_uri = form.get("redirect_uri", [""])[0]
            record = state.codes.pop(code, None)
            if record is None or record.redirect_uri != redirect_uri:
                self._send_json(400, {"error": "invalid_grant"})
                return
            if not verify_pkce_s256(code_verifier, record.code_challenge):
                self._send_json(400, {"error": "invalid_pkce_verifier"})
                return
            access_token = state.mint_access_token()
            id_token = state.mint_id_token(
                client_id=record.client_id, nonce=record.nonce
            )
            self._send_json(
                200,
                {
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "access_token": access_token,
                    "id_token": id_token,
                },
            )

    return _OidcHandler


@pytest.fixture
def oidc_idp() -> Generator[_LoopbackOidcState]:
    """Start a hermetic loopback OIDC Identity Provider for end-to-end testing."""
    key_1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    state = _LoopbackOidcState(issuer="", keys={"kid-1": key_1, "kid-2": key_2})
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_idp_handler(state))
    host = server.server_address[0]
    port = server.server_address[1]
    state.issuer = f"http://{host}:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def test_hermetic_oidc_idp_pkce_discovery_rotation_and_bearer_guard(
    oidc_idp: _LoopbackOidcState,
) -> None:
    """Verify full PKCE + nonce discovery flow, live JWKS rotation, and ID-token block."""
    user_repo = InMemoryUserRepository()
    handlers = UserLifecycleHandlers(
        user_repository=user_repo, token_store=InMemoryTokenStore()
    )
    provider = GenericOidcProvider.from_discovery(
        oidc_idp.issuer, client_id="hexastack-web"
    )
    security = JwksOidcSecurityAdapter.from_discovery(
        oidc_idp.issuer,
        audience="hexastack-api",
        require_access_token_typ=True,
    )

    app = FastAPI()
    app.include_router(
        create_oauth_router(
            provider,
            handlers,
            redirect_uri="http://testserver/auth/oauth/oidc/callback",
        )
    )

    @app.get("/protected")
    def protected_route(
        identity: Annotated[Identity, Depends(require_bearer_token(security))],
    ):
        return {
            "sub": identity.user_id,
            "roles": sorted(identity.roles),
            "permissions": sorted(identity.permissions),
            "tenant_id": identity.tenant_id,
        }

    client = TestClient(app, follow_redirects=False)

    # 1. Start OAuth2 PKCE + nonce authorization via app router
    auth_res = client.get("/auth/oauth/oidc/authorize")
    auth_status = auth_res.status_code
    assert auth_status == 307
    idp_auth_url = auth_res.headers["location"]

    # 2. Simulate browser redirect to hermetic loopback IdP
    idp_res = httpx.get(idp_auth_url, follow_redirects=False, timeout=5.0)
    idp_status = idp_res.status_code
    assert idp_status == 302
    callback_query = urllib.parse.urlparse(idp_res.headers["location"]).query
    params = urllib.parse.parse_qs(callback_query)

    # 3. Complete callback via FastAPI router -> user provisioned with verified claims
    cb_res = client.get(
        "/auth/oauth/oidc/callback",
        params={"code": params["code"][0], "state": params["state"][0]},
    )
    cb_status = cb_res.status_code
    assert cb_status == 200
    saved_user = user_repo.get_by_email("alice@hexastack.dev")
    assert saved_user is not None

    # Replaying state fails closed with 400
    replay_res = client.get(
        "/auth/oauth/oidc/callback",
        params={"code": "unused", "state": params["state"][0]},
    )
    replay_status = replay_res.status_code
    assert replay_status == 400

    # 4. Bearer route accepts valid RS256 access_token (kid-1)
    tok_k1 = oidc_idp.mint_access_token()
    ok_k1 = client.get("/protected", headers={"Authorization": f"Bearer {tok_k1}"})
    ok_k1_status = ok_k1.status_code
    assert ok_k1_status == 200
    assert ok_k1.json()["tenant_id"] == "org-hexastack"

    # 5. Live key rotation on IdP (kid-1 -> kid-2) succeeds automatically
    oidc_idp.rotate_key()
    tok_k2 = oidc_idp.mint_access_token()
    ok_k2 = client.get("/protected", headers={"Authorization": f"Bearer {tok_k2}"})
    ok_k2_status = ok_k2.status_code
    assert ok_k2_status == 200

    # 6. Resource server rejects ID tokens, expired, wrong iss/aud, HS256, and alg=none
    id_tok = oidc_idp.mint_id_token(client_id="hexastack-api", nonce="nonce-leak")
    expired_tok = oidc_idp.mint_access_token(offset_seconds=-60)
    wrong_iss_tok = oidc_idp.mint_access_token(iss="https://other-idp.example.com")
    wrong_aud_tok = oidc_idp.mint_access_token(aud="other-api")
    hs256_tok = jwt.encode(
        {
            "sub": "mallory",
            "iss": oidc_idp.issuer,
            "aud": "hexastack-api",
            "exp": 9999999999,
        },
        "symmetric-secret-key-forged-32bytes!",
        algorithm="HS256",
    )
    alg_none_tok = "eyJhbGciOiJub25lIiwidHlwIjoiYXQrand0In0.eyJzdWIiOiJhIn0."  # pragma: allowlist secret

    for bad_token in (
        id_tok,
        expired_tok,
        wrong_iss_tok,
        wrong_aud_tok,
        hs256_tok,
        alg_none_tok,
    ):
        denied_res = client.get(
            "/protected", headers={"Authorization": f"Bearer {bad_token}"}
        )
        denied_status = denied_res.status_code
        assert denied_status == 401


async def test_hermetic_oidc_idp_rejects_wrong_pkce_verifier(
    oidc_idp: _LoopbackOidcState,
) -> None:
    """Verify upstream loopback IdP rejects token exchange with mismatched verifier."""
    provider = GenericOidcProvider.from_discovery(
        oidc_idp.issuer, client_id="hexastack-cli"
    )
    redirect_uri = "http://127.0.0.1/cb"
    auth_req = provider.create_authorization_request(redirect_uri)
    idp_res = httpx.get(auth_req.url, follow_redirects=False, timeout=5.0)
    code = urllib.parse.parse_qs(
        urllib.parse.urlparse(idp_res.headers["location"]).query
    )["code"][0]

    with pytest.raises(OAuthProviderError, match="invalid_pkce_verifier"):
        await provider.exchange_code(
            code,
            redirect_uri,
            code_verifier="wrong-verifier-value-that-does-not-match-43chars",
            expected_nonce=auth_req.nonce,
        )
