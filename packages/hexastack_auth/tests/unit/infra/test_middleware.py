from dataclasses import dataclass, field

import pytest
from hexastack_auth.domain.exceptions import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from hexastack_auth.domain.models import Identity
from hexastack_auth.infra.decorators import (
    AuthMetadata,
    authorize,
    requires_permission,
    requires_role,
)
from hexastack_auth.infra.middleware import (
    AuthorizationMiddleware,
    _resolve_effective_identity,
    evaluate_authorization,
)
from hexastack_core.domain import Command
from hexastack_core.utils.context import UserContext, set_user_context
from hexastack_cqrs.adapters.buses import SynchronousCommandBus
from hexastack_cqrs.infra.pipeline import create_pipeline
from hexastack_cqrs.infra.registries import CommandRegistry, HandlerRegistry


class PublicCommand(Command):
    message: str


@authorize(require_authenticated=True)
class AuthenticatedOnlyCommand(Command):
    data: str


@requires_role("admin")
class AdminOnlyCommand(Command):
    target_id: str


@requires_permission("invoices:write")
class WriteInvoiceCommand(Command):
    inv_id: str


def test_authorization_middleware_with_anonymous_user():
    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(PublicCommand)
    command_reg.register(AuthenticatedOnlyCommand)

    handler_reg.register(PublicCommand, lambda cmd: f"public: {cmd.message}")
    handler_reg.register(AuthenticatedOnlyCommand, lambda cmd: f"auth: {cmd.data}")

    middleware = AuthorizationMiddleware()
    command_bus = SynchronousCommandBus(handler_reg, middleware=[middleware])

    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        command_bus=command_bus,
    )

    # 1. Public command passes with no context
    res = pipeline.execute(PublicCommand(message="hello"))
    assert res == "public: hello"

    # 2. Authenticated-only command fails when unauthenticated
    with pytest.raises(InvalidCredentialsError):
        pipeline.execute(AuthenticatedOnlyCommand(data="secret"))


def test_authorization_middleware_with_user_context():
    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(AdminOnlyCommand)
    handler_reg.register(AdminOnlyCommand, lambda cmd: f"deleted {cmd.target_id}")

    middleware = AuthorizationMiddleware()
    command_bus = SynchronousCommandBus(handler_reg, middleware=[middleware])

    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        command_bus=command_bus,
    )

    # User without admin role
    set_user_context(UserContext(user_id="user1", roles=["member"]))
    with pytest.raises(InsufficientPermissionsError):
        pipeline.execute(AdminOnlyCommand(target_id="res-123"))

    # User with admin role
    set_user_context(UserContext(user_id="admin1", roles=["admin", "member"]))
    res = pipeline.execute(AdminOnlyCommand(target_id="res-123"))
    assert res == "deleted res-123"


def test_evaluate_authorization_permissions_and_all_matching():
    # Test match_all_roles
    meta_roles = AuthMetadata(roles=("admin", "auditor"), match_all_roles=True)
    ident_missing_role = Identity(user_id="u1", roles=frozenset(["admin"]))
    with pytest.raises(InsufficientPermissionsError):
        evaluate_authorization(meta_roles, ident_missing_role)

    ident_has_both = Identity(user_id="u1", roles=frozenset(["admin", "auditor"]))
    evaluate_authorization(meta_roles, ident_has_both)

    # Test permissions match_all_permissions
    meta_perms_all = AuthMetadata(
        permissions=("read", "write"), match_all_permissions=True
    )
    ident_perm_missing = Identity(user_id="u2", permissions=frozenset(["read"]))
    with pytest.raises(InsufficientPermissionsError):
        evaluate_authorization(meta_perms_all, ident_perm_missing)

    ident_perm_both = Identity(user_id="u2", permissions=frozenset(["read", "write"]))
    evaluate_authorization(meta_perms_all, ident_perm_both)

    # Test permissions match_any_permission
    meta_perms_any = AuthMetadata(
        permissions=("read", "write"), match_all_permissions=False
    )
    with pytest.raises(InsufficientPermissionsError):
        evaluate_authorization(
            meta_perms_any, Identity(user_id="u3", permissions=frozenset(["delete"]))
        )

    evaluate_authorization(
        meta_perms_any, Identity(user_id="u3", permissions=frozenset(["read"]))
    )


def test_resolve_effective_identity_duck_typing():
    @dataclass
    class CustomUser:
        user_id: str = "duck_user"
        roles: list[str] = field(default_factory=lambda: ["duck_role"])
        permissions: list[str] = field(default_factory=lambda: ["duck_perm"])
        tenant_id: str = "tenant_duck"
        is_authenticated: bool = True

    resolved = _resolve_effective_identity(CustomUser())
    assert resolved.user_id == "duck_user"
    assert "duck_role" in resolved.roles
    assert "duck_perm" in resolved.permissions
    assert resolved.tenant_id == "tenant_duck"
    assert resolved.is_authenticated is True


def test_authorization_middleware_disabled():
    middleware = AuthorizationMiddleware(enabled=False)
    cmd = AuthenticatedOnlyCommand(data="bypass")
    res = middleware(cmd, lambda c: "bypassed")
    assert res == "bypassed"


@pytest.mark.anyio
async def test_authorization_middleware_async():
    middleware = AuthorizationMiddleware()
    cmd = PublicCommand(message="async-msg")

    async def _async_handler(c):
        return f"async {c.message}"

    res = await middleware(cmd, _async_handler)
    assert res == "async async-msg"
