from dataclasses import dataclass, field

import pytest

from hexastack_auth.domain.exceptions import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from hexastack_auth.domain.models import AnonymousIdentity, Identity
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


@pytest.mark.anyio
async def test_authorization_middleware_async():
    middleware = AuthorizationMiddleware()
    cmd_pub = PublicCommand(message="async-msg")

    async def _async_handler(c):
        return f"async {c.message}"

    res = await middleware(cmd_pub, _async_handler)
    assert res == "async async-msg"

    # Async unauthorized command fails
    set_user_context(None)
    cmd_auth = AuthenticatedOnlyCommand(data="async-secret")
    with pytest.raises(InvalidCredentialsError):
        await middleware(cmd_auth, _async_handler)


def test_authorization_middleware_disabled():
    middleware = AuthorizationMiddleware(enabled=False)
    assert middleware.enabled is False
    cmd = AuthenticatedOnlyCommand(data="bypass")
    res = middleware(cmd, lambda c: "bypassed")
    assert res == "bypassed"


def test_authorization_middleware_with_anonymous_user():
    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(PublicCommand)
    command_reg.register(AuthenticatedOnlyCommand)

    handler_reg.register(PublicCommand, lambda cmd: f"public: {cmd.message}")
    handler_reg.register(AuthenticatedOnlyCommand, lambda cmd: f"auth: {cmd.data}")

    middleware = AuthorizationMiddleware()
    assert middleware.enabled is True
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
    with pytest.raises(
        InvalidCredentialsError, match="Authentication credentials are required"
    ):
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
    with pytest.raises(
        InsufficientPermissionsError, match="lacks required roles: \\['admin'\\]"
    ):
        pipeline.execute(AdminOnlyCommand(target_id="res-123"))

    # User with admin role
    set_user_context(UserContext(user_id="admin1", roles=["admin", "member"]))
    res = pipeline.execute(AdminOnlyCommand(target_id="res-123"))
    assert res == "deleted res-123"


def test_evaluate_authorization_permissions_all_and_any():
    # Test match_all_permissions = True
    meta_perms_all = AuthMetadata(
        permissions=("read", "write"), match_all_permissions=True
    )
    ident_perm_missing = Identity(user_id="u2", permissions=frozenset(["read"]))
    with pytest.raises(
        InsufficientPermissionsError,
        match="lacks required permissions: \\['read', 'write'\\]",
    ):
        evaluate_authorization(meta_perms_all, ident_perm_missing)

    ident_perm_both = Identity(user_id="u2", permissions=frozenset(["read", "write"]))
    evaluate_authorization(meta_perms_all, ident_perm_both)

    # Test match_all_permissions = False (any permission)
    meta_perms_any = AuthMetadata(
        permissions=("read", "write"), match_all_permissions=False
    )
    with pytest.raises(
        InsufficientPermissionsError,
        match="lacks any of the required permissions: \\['read', 'write'\\]",
    ):
        evaluate_authorization(
            meta_perms_any,
            Identity(user_id="u3", permissions=frozenset(["delete"])),
        )

    evaluate_authorization(
        meta_perms_any, Identity(user_id="u3", permissions=frozenset(["read"]))
    )


def test_evaluate_authorization_roles_all_and_any():
    # Test match_all_roles = True
    meta_roles_all = AuthMetadata(roles=("admin", "auditor"), match_all_roles=True)
    ident_missing_role = Identity(user_id="u1", roles=frozenset(["admin"]))
    with pytest.raises(
        InsufficientPermissionsError,
        match="lacks required roles: \\['admin', 'auditor'\\]",
    ):
        evaluate_authorization(meta_roles_all, ident_missing_role)

    ident_has_both = Identity(user_id="u1", roles=frozenset(["admin", "auditor"]))
    evaluate_authorization(meta_roles_all, ident_has_both)

    # Test match_all_roles = False (any role)
    meta_roles_any = AuthMetadata(roles=("admin", "auditor"), match_all_roles=False)
    ident_has_none = Identity(user_id="u1", roles=frozenset(["viewer"]))
    with pytest.raises(
        InsufficientPermissionsError,
        match="lacks any of the required roles: \\['admin', 'auditor'\\]",
    ):
        evaluate_authorization(meta_roles_any, ident_has_none)

    ident_has_one = Identity(user_id="u1", roles=frozenset(["viewer", "admin"]))
    evaluate_authorization(meta_roles_any, ident_has_one)


def test_resolve_effective_identity_variations():
    # 1. None context -> AnonymousIdentity
    set_user_context(None)
    resolved_none = _resolve_effective_identity(None)
    assert isinstance(resolved_none, AnonymousIdentity)
    assert resolved_none.is_authenticated is False

    # 2. Direct Identity
    direct_id = Identity(user_id="direct_u", is_authenticated=True)
    assert _resolve_effective_identity(direct_id) is direct_id

    # 3. UserContext
    uctx = UserContext(user_id="ctx_u", roles=["admin"], tenant_id="t1")
    resolved_ctx = _resolve_effective_identity(uctx)
    assert resolved_ctx.user_id == "ctx_u"
    assert "admin" in resolved_ctx.roles
    assert resolved_ctx.tenant_id == "t1"
    assert resolved_ctx.is_authenticated is True

    # 4. Duck-typed object
    @dataclass
    class CustomUser:
        user_id: str = "duck_user"
        roles: list[str] = field(default_factory=lambda: ["duck_role"])
        permissions: list[str] = field(default_factory=lambda: ["duck_perm"])
        tenant_id: str = "tenant_duck"
        is_authenticated: bool = True

    resolved_duck = _resolve_effective_identity(CustomUser())
    assert resolved_duck.user_id == "duck_user"
    assert "duck_role" in resolved_duck.roles
    assert "duck_perm" in resolved_duck.permissions
    assert resolved_duck.tenant_id == "tenant_duck"
    assert resolved_duck.is_authenticated is True
