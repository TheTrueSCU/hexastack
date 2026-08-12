from hexastack_core.domain import Command, Query
from hexastack_fastapi.infra.decorators import (
    _ROUTE_METADATA_ATTR,
    RouteMetadata,
    api_command,
    api_query,
)


@api_command(
    "/accounts/create",
    method="POST",
    status_code=201,
    output_format="json",
    summary="Create an account",
    tags=["Accounts"],
)
class CreateAccountCmd(Command):
    account_id: str


@api_query(
    "/accounts/{account_id}",
    method="GET",
    status_code=200,
    output_format="json",
    summary="Fetch an account",
    tags=["Accounts"],
)
class GetAccountQry(Query):
    account_id: str


def test_api_command_decorator_attaches_metadata():
    meta: RouteMetadata = getattr(CreateAccountCmd, _ROUTE_METADATA_ATTR)
    assert meta.path == "/accounts/create"
    assert meta.kind == "command"
    assert meta.method == "POST"
    assert meta.status_code == 201
    assert meta.output_format == "json"
    assert meta.summary == "Create an account"
    assert meta.tags == ("Accounts",)


def test_api_query_decorator_attaches_metadata():
    meta: RouteMetadata = getattr(GetAccountQry, _ROUTE_METADATA_ATTR)
    assert meta.path == "/accounts/{account_id}"
    assert meta.kind == "query"
    assert meta.method == "GET"
    assert meta.status_code == 200
    assert meta.output_format == "json"
    assert meta.summary == "Fetch an account"
    assert meta.tags == ("Accounts",)
