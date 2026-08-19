"""FastAPI route guard dependencies for hexastack-auth (OPA & OpenFGA).

Notes/Architectural Intent:
    Provides direct HTTP route-level policy and relationship guards for FastAPI.
    FastAPI is an optional dependency of hexastack-auth[fastapi].
"""

import importlib.util
from typing import Any

from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.utils.context import get_user_context

__all__ = [
    "require_policy",
    "require_relation",
]


def _require_fastapi() -> None:
    if importlib.util.find_spec("fastapi") is None:
        raise MissingDependencyError(
            "fastapi is required for FastAPI auth dependencies. "
            "Install with 'pip install hexastack-auth[fastapi]'."
        )


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
    from fastapi import HTTPException, Request

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
    from fastapi import HTTPException, Request

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
