import types

from typer.testing import CliRunner

from hexastack_cli.adapters.app import create_cli_app
from hexastack_cli.infra.autodiscovery import (
    autodiscover_cli_commands,
)
from hexastack_cli.infra.decorators import cli_command, cli_group, cli_query
from hexastack_core.domain import Command, Generic, Query
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry


@cli_group("user", help="User account administration")
class UserGroupConfig:
    pass


@cli_command(
    "new",
    aliases=["create", "account.new", "/signup"],
    help="Create a new user account",
    group="user",
)
class CreateUserCommand(Command):
    name: str


@cli_query(
    "get",
    aliases=["find", "search.user"],
    help="Get user account by name",
    group="user",
)
class GetUserQuery(Query[str]):
    name: str


@cli_command("set-bio", help="Set user profile biography", group="user.profile")
class SetBioCommand(Command):
    bio: str


class UserDTO(Generic):
    username: str


class BioDTO(Generic):
    status: str


def test_autodiscover_cli_commands_nested_subgroups_and_aliases():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUserCommand,
        lambda cmd: UserDTO(username=f"Created user: {cmd.name}"),
    )
    handler_reg.register(GetUserQuery, lambda qry: f"Found user {qry.name}")
    handler_reg.register(
        SetBioCommand, lambda cmd: BioDTO(status=f"Updated bio to: {cmd.bio}")
    )

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    app = create_cli_app()
    mod = types.ModuleType("sample_nested_cli_module")
    mod.__dict__["UserGroupConfig"] = UserGroupConfig
    mod.__dict__["CreateUserCommand"] = CreateUserCommand
    mod.__dict__["GetUserQuery"] = GetUserQuery
    mod.__dict__["SetBioCommand"] = SetBioCommand

    autodiscover_cli_commands(app, [mod], pipeline=pipeline)

    runner = CliRunner()

    # 1. Root --help shows 'user' group, 'account' group (from cross-group alias), and 'signup' (from root alias)
    res_root_help = runner.invoke(app, ["--help"])
    assert res_root_help.exit_code == 0
    assert "user" in res_root_help.stdout
    assert "account" in res_root_help.stdout
    assert "signup" in res_root_help.stdout

    # 2. 'user' --help shows primary 'new', intra-group alias 'create', primary 'get', and alias 'find'
    res_user_help = runner.invoke(app, ["user", "--help"])
    assert res_user_help.exit_code == 0
    assert "new" in res_user_help.stdout
    assert "create" in res_user_help.stdout
    assert "get" in res_user_help.stdout
    assert "find" in res_user_help.stdout
    assert "profile" in res_user_help.stdout

    # 3. Execute Primary: app user new --name richard
    res_cmd = runner.invoke(app, ["user", "new", "--name", "richard"])
    assert res_cmd.exit_code == 0
    assert "Created user: richard" in res_cmd.stdout

    # 4. Execute Intra-group Alias: app user create --name richard
    res_alias_intra = runner.invoke(app, ["user", "create", "--name", "richard"])
    assert res_alias_intra.exit_code == 0
    assert "Created user: richard" in res_alias_intra.stdout

    # 5. Execute Cross-group Alias: app account new --name richard
    res_alias_cross = runner.invoke(app, ["account", "new", "--name", "richard"])
    assert res_alias_cross.exit_code == 0
    assert "Created user: richard" in res_alias_cross.stdout

    # 6. Execute Root-level Alias: app signup --name richard
    res_alias_root = runner.invoke(app, ["signup", "--name", "richard"])
    assert res_alias_root.exit_code == 0
    assert "Created user: richard" in res_alias_root.stdout

    # 7. Execute Query and Cross-group Query Alias
    res_qry = runner.invoke(app, ["user", "find", "--name", "richard"])
    assert res_qry.exit_code == 0
    assert "Found user richard" in res_qry.stdout

    res_cross_qry = runner.invoke(app, ["search", "user", "--name", "richard"])
    assert res_cross_qry.exit_code == 0
    assert "Found user richard" in res_cross_qry.stdout

    # 8. Execute multi-level nested command: app user profile set-bio --bio "Engineer"
    res_nested = runner.invoke(app, ["user", "profile", "set-bio", "--bio", "Engineer"])
    assert res_nested.exit_code == 0
    assert "Updated bio to: Engineer" in res_nested.stdout


def test_cli_autodiscovery_internal_helpers():
    from hexastack_cli.infra.autodiscovery import (
        _normalize_group_path,
        _resolve_targets,
        _SubgroupManager,
    )
    from hexastack_cli.infra.decorators import CliMetadata

    # 1. _normalize_group_path
    assert _normalize_group_path(None) == []
    assert _normalize_group_path("") == []
    assert _normalize_group_path("user.profile.details") == [
        "user",
        "profile",
        "details",
    ]
    assert _normalize_group_path("user/admin profile") == ["user", "admin", "profile"]
    assert _normalize_group_path([" user ", " profile "]) == ["user", "profile"]

    # 2. _resolve_targets
    meta = CliMetadata(
        name="custom-name",
        kind="command",
        group="admin.users",
        aliases=("add", "/root-create", "super/admin/make"),
        help="Custom help",
    )
    targets = _resolve_targets(meta, default_name="fallback-name")
    assert targets == [
        (["admin", "users"], "custom-name", "Custom help"),
        (["admin", "users"], "add", "Custom help"),
        ([], "root-create", "Custom help"),
        (["super", "admin"], "make", "Custom help"),
    ]

    # 3. _SubgroupManager
    root_app = create_cli_app()
    manager = _SubgroupManager(root_app)
    assert manager.get_or_create([]) is root_app

    sub_app = manager.get_or_create(["billing", "invoices"])
    assert sub_app is not None
    # Idempotent retrieval
    assert manager.get_or_create(["billing", "invoices"]) is sub_app
