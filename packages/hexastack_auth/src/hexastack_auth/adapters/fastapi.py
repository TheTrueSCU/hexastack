"""FastAPI route guard dependencies and authentication router generators for hexastack-auth.

Notes/Architectural Intent:
    Provides HTTP route guards (OPA policies, OpenFGA relations) and turnkey
    FastAPI router generators (`create_auth_router`, `create_oauth_router`)
    exposing CQRS user lifecycle endpoints with cookie and bearer token transports.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Collection
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from hexastack_auth.domain.commands import (
    AuthenticateUserQuery,
    OAuthLoginCommand,
    RegisterUserCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    VerifyEmailCommand,
)
from hexastack_auth.domain.exceptions import (
    AccountInactiveError,
    AuthError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_auth.ports.security import SecurityPort
from hexastack_core.utils.context import (
    UserContext,
    get_user_context,
    set_user_context,
)
from hexastack_core.utils.imports import optional_dependency, require_dependency

_fastapi_mod = optional_dependency("fastapi")
Request = getattr(_fastapi_mod, "Request", Any)
Response = getattr(_fastapi_mod, "Response", Any)

if TYPE_CHECKING:
    from fastapi import APIRouter

    from hexastack_auth.adapters.handlers import UserLifecycleHandlers
    from hexastack_auth.adapters.jwt import JwtSecurityAdapter
    from hexastack_auth.ports.user import OAuthProviderPort


def _require_fastapi() -> Any:
    return require_dependency(
        "fastapi",
        extra="fastapi",
        package="hexastack-auth",
        feature_name="FastAPI auth dependencies",
    )


# DTO Schemas for HTTP Transport
class RegisterRequest(BaseModel):
    """HTTP payload schema for user registration requests.

    Notes/Architectural Intent:
        Validates raw registration payload ensuring minimum password length
        before propagating to CQRS RegisterUserCommand.
    """

    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """HTTP payload schema for credential-based authentication.

    Notes/Architectural Intent:
        Transports login credentials from HTTP client to AuthenticateUserQuery.
    """

    email: str
    password: str


class VerifyRequest(BaseModel):
    """HTTP payload schema for email verification submission.

    Notes/Architectural Intent:
        Transports raw token parameter to VerifyEmailCommand for consumption.
    """

    token: str


class ForgotPasswordRequest(BaseModel):
    """HTTP payload schema for requesting a password reset email.

    Notes/Architectural Intent:
        Accepts registered email to issue recovery token without enumerating accounts.
    """

    email: str


class ResetPasswordRequest(BaseModel):
    """HTTP payload schema for submitting a new password with reset token.

    Notes/Architectural Intent:
        Enforces 8-character password constraint during recovery completion.
    """

    token: str
    new_password: str = Field(min_length=8)


class UserResponse(BaseModel):
    """HTTP serialized response schema representing a User entity.

    Notes/Architectural Intent:
        Exposes public identity fields while strictly omitting sensitive password hashes.
    """

    id: str
    email: str
    roles: list[str]
    is_active: bool
    is_verified: bool


class TokenResponse(BaseModel):
    """HTTP response schema containing an issued bearer access token.

    Notes/Architectural Intent:
        Formats bearer token response compliant with OAuth2 token endpoint specification.
    """

    access_token: str
    token_type: str = "bearer"  # noqa: S105


def require_policy(
    policy_path: str,
    *,
    resource: str = "http_request",
    status_code: int = 403,
    detail: str | None = None,
) -> Any:
    """FastAPI route guard dependency enforcing an OPA or custom policy check.

    Args:
        policy_path: OPA policy endpoint (e.g. 'v1/data/reports/view').
        resource: Target resource string.
        status_code: HTTP status code to return when denied (defaults to 403).
        detail: Custom error detail message.

    Returns:
        FastAPI async dependency callable.
    """
    _require_fastapi()
    from fastapi import HTTPException

    async def _dependency(request: Request) -> None:
        container = getattr(request.app.state, "container", None)
        if container is None or AuthorizationPolicyPort not in container:
            raise HTTPException(
                status_code=500,
                detail="AuthorizationPolicyPort is not configured in DI container.",
            )

        policy_port = container.resolve(AuthorizationPolicyPort)
        user_ctx = get_user_context()
        identity = Identity(
            user_id=user_ctx.user_id if user_ctx else "anonymous",
            roles=frozenset(user_ctx.roles if user_ctx else ()),
            tenant_id=user_ctx.tenant_id if user_ctx else None,
            is_authenticated=bool(user_ctx and user_ctx.user_id),
        )

        allowed = policy_port.is_authorized(
            identity=identity,
            action=policy_path,
            resource=resource,
            context={"url": str(request.url), "method": request.method},
        )
        if not allowed:
            raise HTTPException(
                status_code=status_code,
                detail=detail or f"Access denied by policy '{policy_path}'.",
            )

    return _dependency


def require_relation(
    relation: str,
    object_type: str,
    object_id: str | None = None,
    *,
    status_code: int = 403,
    detail: str | None = None,
) -> Any:
    """FastAPI route guard dependency enforcing an OpenFGA relationship check.

    Args:
        relation: OpenFGA relationship name (e.g. 'can_edit', 'viewer').
        object_type: Target object type (e.g. 'document', 'project').
        object_id: Explicit object identifier or None.
        status_code: HTTP status code to return when denied (defaults to 403).
        detail: Custom error detail message.

    Returns:
        FastAPI async dependency callable.
    """
    _require_fastapi()
    from fastapi import HTTPException

    async def _dependency(request: Request) -> None:
        container = getattr(request.app.state, "container", None)
        if container is None or AuthorizationPolicyPort not in container:
            raise HTTPException(
                status_code=500,
                detail="AuthorizationPolicyPort is not configured in DI container.",
            )

        policy_port = container.resolve(AuthorizationPolicyPort)
        user_ctx = get_user_context()
        identity = Identity(
            user_id=user_ctx.user_id if user_ctx else "anonymous",
            roles=frozenset(user_ctx.roles if user_ctx else ()),
            tenant_id=user_ctx.tenant_id if user_ctx else None,
            is_authenticated=bool(user_ctx and user_ctx.user_id),
        )

        target_obj = f"{object_type}:{object_id or 'default'}"
        allowed = policy_port.is_authorized(
            identity=identity,
            action=relation,
            resource=target_obj,
        )
        if not allowed:
            raise HTTPException(
                status_code=status_code,
                detail=detail
                or f"Access denied: missing '{relation}' on '{target_obj}'.",
            )

    return _dependency


def require_bearer_token(
    security_port: SecurityPort | None = None,
    *,
    required_roles: Collection[str] | None = None,
    required_permissions: Collection[str] | None = None,
) -> Any:
    """FastAPI route dependency enforcing Bearer token authentication and RBAC.

    Args:
        security_port: Optional explicit ``SecurityPort`` adapter (resolves from
            ``request.app.state.container`` when omitted).
        required_roles: Optional collection of roles the caller must hold.
        required_permissions: Optional collection of permissions the caller must hold.

    Returns:
        FastAPI async dependency callable returning the verified ``Identity``.

    Notes/Architectural Intent:
        Supports ``JwksOidcSecurityAdapter``, ``JwtSecurityAdapter``, or any
        ``SecurityPort`` implementation via constructor or DI container injection,
        populating ambient ``UserContext`` for downstream CQRS/logging layers.
    """
    _require_fastapi()
    from fastapi import HTTPException, status

    async def _dependency(request: Request) -> Identity:
        auth_header = request.headers.get("Authorization") or ""
        scheme, _, raw_token = auth_header.strip().partition(" ")
        token = raw_token.strip()
        if scheme.casefold() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Bearer authentication header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        resolved_port = security_port
        if resolved_port is None:
            container = getattr(request.app.state, "container", None)
            if container is None or SecurityPort not in container:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="SecurityPort is not configured in DI container.",
                )
            resolved_port = container.resolve(SecurityPort)

        try:
            identity = resolved_port.verify_token(token)
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if required_roles and not identity.has_all_roles(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges.",
            )
        if required_permissions and not identity.has_all_permissions(
            required_permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        set_user_context(
            UserContext(
                user_id=identity.user_id,
                roles=sorted(identity.roles),
                tenant_id=identity.tenant_id,
            )
        )
        return identity

    return _dependency


def create_auth_router(
    handlers: UserLifecycleHandlers,
    jwt_adapter: JwtSecurityAdapter | None = None,
    cookie_name: str | None = None,
    prefix: str = "/auth",
    tags: list[str | Enum] | None = None,
) -> APIRouter:
    """Generate a turnkey FastAPI APIRouter exposing CQRS user lifecycle endpoints.

    Args:
        handlers: UserLifecycleHandlers coordinator.
        jwt_adapter: Optional JwtSecurityAdapter for issuing bearer tokens.
        cookie_name: Optional cookie name for session token persistence.
        prefix: URL route prefix (default '/auth').
        tags: Swagger/OpenAPI documentation tags.

    Returns:
        Ready-to-mount FastAPI APIRouter instance.
    """
    _require_fastapi()
    from fastapi import APIRouter, HTTPException, status

    router = APIRouter(prefix=prefix, tags=tags or ["Authentication"])

    @router.post(
        "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
    )
    async def register(req: RegisterRequest) -> UserResponse:
        cmd = RegisterUserCommand(email=str(req.email), password=req.password)
        try:
            user, _ = await handlers.register_user_async(cmd)
            return UserResponse(
                id=user.id,
                email=user.email,
                roles=list(user.roles),
                is_active=user.is_active,
                is_verified=user.is_verified,
            )
        except UserAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc

    @router.post("/login", response_model=TokenResponse)
    async def login(req: LoginRequest, response: Response) -> TokenResponse:
        query = AuthenticateUserQuery(email=str(req.email), password=req.password)
        try:
            user = await handlers.authenticate_user_async(query)
        except InvalidCredentialsError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            ) from exc
        except AccountInactiveError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc

        if jwt_adapter is not None:
            token = jwt_adapter.create_token(user.to_identity())
        else:
            token = secrets.token_urlsafe(32)

        if cookie_name is not None:
            response.set_cookie(cookie_name, token, httponly=True, secure=True)

        return TokenResponse(access_token=token)

    @router.post("/verify", response_model=UserResponse)
    async def verify(req: VerifyRequest) -> UserResponse:
        cmd = VerifyEmailCommand(token=req.token)
        try:
            user = await handlers.verify_email_async(cmd)
            return UserResponse(
                id=user.id,
                email=user.email,
                roles=list(user.roles),
                is_active=user.is_active,
                is_verified=user.is_verified,
            )
        except (InvalidTokenError, UserNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

    @router.post("/forgot-password")
    async def forgot_password(req: ForgotPasswordRequest) -> dict[str, str]:
        cmd = RequestPasswordResetCommand(email=str(req.email))
        await handlers.request_password_reset_async(cmd)
        return {
            "status": "ok",
            "message": "If the email is registered, a password reset link has been issued.",
        }

    @router.post("/reset-password", response_model=UserResponse)
    async def reset_password(req: ResetPasswordRequest) -> UserResponse:
        cmd = ResetPasswordCommand(token=req.token, new_password=req.new_password)
        try:
            user = await handlers.reset_password_async(cmd)
            return UserResponse(
                id=user.id,
                email=user.email,
                roles=list(user.roles),
                is_active=user.is_active,
                is_verified=user.is_verified,
            )
        except (InvalidTokenError, UserNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

    return router


def create_oauth_router(
    oauth_provider: OAuthProviderPort,
    handlers: UserLifecycleHandlers,
    jwt_adapter: JwtSecurityAdapter | None = None,
    redirect_uri: str = "http://localhost:8000/auth/oauth/callback",
    prefix: str = "/auth/oauth",
    tags: list[str | Enum] | None = None,
    *,
    use_pkce: bool = True,
    use_nonce: bool = True,
    require_state: bool = True,
    state_ttl_seconds: int = 300,
) -> APIRouter:
    """Generate a turnkey FastAPI APIRouter for social OAuth2 / OIDC login workflows.

    Args:
        oauth_provider: Concrete OAuthProviderPort instance (Google, GitHub, OIDC).
        handlers: UserLifecycleHandlers coordinator.
        jwt_adapter: Optional JwtSecurityAdapter for issuing bearer tokens.
        redirect_uri: Registered callback URL.
        prefix: URL prefix.
        tags: OpenAPI tags.
        use_pkce: Attach RFC 7636 ``S256`` PKCE challenge/verifier across redirects.
        use_nonce: Attach OIDC ``nonce`` binding across authorization and callback.
        require_state: Validate and consume single-use anti-CSRF ``state`` tokens.
        state_ttl_seconds: Lifetime of ephemeral pending authorization transactions.

    Returns:
        Ready-to-mount FastAPI APIRouter instance.

    Notes/Architectural Intent:
        Stores single-use pending PKCE verifier and OIDC nonce state per transaction
        keyed by CSPRNG ``state`` so replay, CSRF, and authorization-code injection
        attacks fail closed at the HTTP callback boundary.
    """
    _require_fastapi()
    from fastapi import APIRouter, HTTPException, status
    from fastapi.responses import RedirectResponse

    router = APIRouter(prefix=prefix, tags=tags or [f"OAuth ({oauth_provider.name})"])
    pending_states: dict[str, tuple[str | None, str | None, float]] = {}

    def _prune_expired(now: float) -> None:
        expired_keys = [
            key for key, (_, _, exp) in pending_states.items() if exp <= now
        ]
        for key in expired_keys:
            pending_states.pop(key, None)

    @router.get(f"/{oauth_provider.name}/authorize")
    async def authorize() -> RedirectResponse:
        now = time.monotonic()
        _prune_expired(now)
        auth_req = oauth_provider.create_authorization_request(
            redirect_uri=redirect_uri,
            use_pkce=use_pkce,
            use_nonce=use_nonce,
        )
        pending_states[auth_req.state] = (
            auth_req.code_verifier,
            auth_req.nonce,
            now + max(1, state_ttl_seconds),
        )
        return RedirectResponse(url=auth_req.url)

    @router.get(f"/{oauth_provider.name}/callback", response_model=TokenResponse)
    async def callback(code: str, state: str | None = None) -> TokenResponse:
        now = time.monotonic()
        _prune_expired(now)
        entry = pending_states.pop(state, None) if state is not None else None
        if require_state and entry is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, missing, or expired OAuth state parameter.",
            )

        code_verifier, expected_nonce, _ = (
            entry if entry is not None else (None, None, 0.0)
        )
        exchange_kwargs: dict[str, Any] = {}
        if code_verifier is not None:
            exchange_kwargs["code_verifier"] = code_verifier
        if expected_nonce is not None:
            exchange_kwargs["expected_nonce"] = expected_nonce

        try:
            user_info = await oauth_provider.exchange_code(
                code=code, redirect_uri=redirect_uri, **exchange_kwargs
            )
            cmd = OAuthLoginCommand(provider=oauth_provider.name, oauth_user=user_info)
            user = await handlers.oauth_login_async(cmd)
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

        if jwt_adapter is not None:
            token = jwt_adapter.create_token(user.to_identity())
        else:
            token = secrets.token_urlsafe(32)

        return TokenResponse(access_token=token)

    return router


__all__ = [
    "create_auth_router",
    "create_oauth_router",
    "ForgotPasswordRequest",
    "LoginRequest",
    "RegisterRequest",
    "require_bearer_token",
    "require_policy",
    "require_relation",
    "ResetPasswordRequest",
    "TokenResponse",
    "UserResponse",
    "VerifyRequest",
]
