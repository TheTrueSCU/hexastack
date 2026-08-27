from hexastack_cli.infra.decorators import (
    _CLI_GROUP_ATTR,
    _CLI_METADATA_ATTR,
    CliMetadata,
    GroupMetadata,
    cli_command,
    cli_group,
    cli_query,
)
from hexastack_core.domain import Command, Query


@cli_group("users", help="User management commands")
class UserGroupConfig:
    pass


@cli_command(
    "make-user",
    positional=["username"],
    help="Create a new user",
    group="users",
)
class CreateUserCommand(Command):
    username: str


@cli_query(
    "find-user",
    positional="user_id",
    help="Find user by ID",
    group="users.search",
)
class FindUserQuery(Query[str]):
    user_id: str


def test_cli_command_decorator():
    meta: CliMetadata = getattr(CreateUserCommand, _CLI_METADATA_ATTR)
    assert meta.kind == "command"
    assert meta.name == "make-user"
    assert meta.positional == ("username",)
    assert meta.help == "Create a new user"
    assert meta.group == "users"


def test_cli_command_with_feature_flag():
    @cli_command("secret-task", feature_flag="flags.secret_cli")
    class SecretTaskCommand(Command):
        name: str

    meta: CliMetadata = getattr(SecretTaskCommand, _CLI_METADATA_ATTR)
    assert meta.feature_flag == "flags.secret_cli"


def test_cli_group_decorator():
    meta: GroupMetadata = getattr(UserGroupConfig, _CLI_GROUP_ATTR)
    assert meta.name == "users"
    assert meta.help == "User management commands"


def test_cli_query_decorator():
    meta: CliMetadata = getattr(FindUserQuery, _CLI_METADATA_ATTR)
    assert meta.kind == "query"
    assert meta.name == "find-user"
    assert meta.positional == ("user_id",)
    assert meta.help == "Find user by ID"
    assert meta.group == "users.search"


def test_feature_flag_command_decorator():
    import typer
    from typer.testing import CliRunner

    from hexastack_cli.infra.decorators import feature_flag_command

    app = typer.Typer()

    @app.command("beta")
    @feature_flag_command("cli.beta_tool")
    def beta_cmd():
        typer.echo("beta success")

    runner = CliRunner()

    # 1. In Typer with multiple commands, invoke with command name; for single command app, invoke with []
    res_disabled = runner.invoke(app, [])
    assert res_disabled.exit_code == 1
    assert (
        "disabled by feature flag" in res_disabled.stderr
        or "disabled by feature flag" in res_disabled.stdout
    )


def test_feature_flag_command_direct_invocation():
    """Verify feature_flag_command gating on CLI functions directly."""
    import pytest
    import typer

    from hexastack_cli.infra.decorators import feature_flag_command

    @feature_flag_command("cli.active_feature", default=True)
    def active_cmd():
        return "active-ok"

    assert active_cmd() == "active-ok"

    @feature_flag_command("cli.inactive_feature", default=False)
    def inactive_cmd():
        return "inactive-ok"

    with pytest.raises(typer.Exit) as exc_info:
        inactive_cmd()
    assert exc_info.value.exit_code == 1
