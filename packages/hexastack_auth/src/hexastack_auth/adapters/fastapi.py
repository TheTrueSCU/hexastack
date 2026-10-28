"""FastAPI route guard dependencies and authentication router generators for hexastack-auth.

Notes/Architectural Intent:
    Provides HTTP route guards (OPA policies, OpenFGA relations) and turnkey
    FastAPI router generators (`create_auth_router`, `create_oauth_router`)
    exposing CQRS user lifecycle endpoints with cookie and bearer token transports.
"""

from __future__ import annotations

import secrets
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
from hexastack_core.utils.context import get_user_context
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
) -> APIRouter:
    """Generate a turnkey FastAPI APIRouter for social OAuth2 / OIDC login workflows.

    Args:
        oauth_provider: Concrete OAuthProviderPort instance (Google, GitHub, OIDC).
        handlers: UserLifecycleHandlers coordinator.
        jwt_adapter: Optional JwtSecurityAdapter for issuing bearer tokens.
        redirect_uri: Registered callback URL.
        prefix: URL prefix.
        tags: OpenAPI tags.

    Returns:
        Ready-to-mount FastAPI APIRouter instance.
    """
    _require_fastapi()
    from fastapi import APIRouter, HTTPException, status
    from fastapi.responses import RedirectResponse

    router = APIRouter(prefix=prefix, tags=tags or [f"OAuth ({oauth_provider.name})"])

    @router.get(f"/{oauth_provider.name}/authorize")
    async def authorize() -> RedirectResponse:
        state = secrets.token_urlsafe(16)
        auth_url = oauth_provider.get_authorization_url(
            state=state, redirect_uri=redirect_uri
        )
        return RedirectResponse(url=auth_url)

    @router.get(f"/{oauth_provider.name}/callback", response_model=TokenResponse)
    async def callback(code: str, state: str | None = None) -> TokenResponse:
        try:
            user_info = await oauth_provider.exchange_code(
                code=code, redirect_uri=redirect_uri
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
    "require_policy",
    "require_relation",
    "ResetPasswordRequest",
    "TokenResponse",
    "UserResponse",
    "VerifyRequest",
]
