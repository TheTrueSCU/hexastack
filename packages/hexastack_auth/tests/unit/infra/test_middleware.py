import pytest
from hexastack_auth.domain.exceptions import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from hexastack_auth.infra.decorators import authorize, requires_role
from hexastack_auth.infra.middleware import AuthorizationMiddleware
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
