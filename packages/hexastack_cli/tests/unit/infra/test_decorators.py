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


def test_cli_group_decorator():
    meta: GroupMetadata = getattr(UserGroupConfig, _CLI_GROUP_ATTR)
    assert meta.name == "users"
    assert meta.help == "User management commands"


def test_cli_command_decorator():
    meta: CliMetadata = getattr(CreateUserCommand, _CLI_METADATA_ATTR)
    assert meta.kind == "command"
    assert meta.name == "make-user"
    assert meta.positional == ("username",)
    assert meta.help == "Create a new user"
    assert meta.group == "users"


def test_cli_query_decorator():
    meta: CliMetadata = getattr(FindUserQuery, _CLI_METADATA_ATTR)
    assert meta.kind == "query"
    assert meta.name == "find-user"
    assert meta.positional == ("user_id",)
    assert meta.help == "Find user by ID"
    assert meta.group == "users.search"
