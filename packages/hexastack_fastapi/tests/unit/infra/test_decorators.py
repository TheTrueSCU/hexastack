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


def test_api_command_with_feature_flag():
    @api_command("/gated-cmd", feature_flag="flags.gated_cmd")
    class GatedCmd(Command):
        pass

    meta: RouteMetadata = getattr(GatedCmd, _ROUTE_METADATA_ATTR)
    assert meta.feature_flag == "flags.gated_cmd"


def test_api_query_decorator_attaches_metadata():
    meta: RouteMetadata = getattr(GetAccountQry, _ROUTE_METADATA_ATTR)
    assert meta.path == "/accounts/{account_id}"
    assert meta.kind == "query"
    assert meta.method == "GET"
    assert meta.status_code == 200
    assert meta.output_format == "json"
    assert meta.summary == "Fetch an account"
    assert meta.tags == ("Accounts",)


def test_feature_flag_route_decorator():
    import pytest
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.testclient import TestClient
    from rodi import Container

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_fastapi.infra.decorators import feature_flag_route

    flags = InMemoryFeatureFlagAdapter({"flags.custom_route": False})
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)

    app = FastAPI()
    app.state.container = container

    @app.get("/custom-route")
    @feature_flag_route("flags.custom_route")
    async def custom_route(request: Request):
        return {"hello": "world"}

    client = TestClient(app)

    # 1. Disabled returns 404
    res_disabled = client.get("/custom-route")
    assert res_disabled.status_code == 404

    # 2. Enabled dynamically returns 200
    flags.set_flag("flags.custom_route", True)
    res_enabled = client.get("/custom-route")
    assert res_enabled.status_code == 200
    assert res_enabled.json() == {"hello": "world"}

    # 3. Synchronous wrapped route
    @feature_flag_route("flags.custom_route")
    def sync_route(request: Request):
        return "sync ok"

    req = Request(scope={"type": "http", "app": app})
    assert sync_route(request=req) == "sync ok"

    flags.set_flag("flags.custom_route", False)
    with pytest.raises(HTTPException):
        sync_route(request=req)
