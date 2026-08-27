import pytest

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

    # 4. Fallback when request is None (uses ConfigFeatureFlagAdapter)
    @feature_flag_route("flags.missing_flag", default=True)
    async def async_no_req():
        return "default ok"

    import asyncio

    assert asyncio.run(async_no_req()) == "default ok"

    @feature_flag_route(
        "flags.missing_flag", default=False, status_code=403, detail="Forbidden feature"
    )
    def sync_no_req():
        return "forbidden"

    with pytest.raises(HTTPException) as exc_info:
        sync_no_req()
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden feature"


@pytest.mark.anyio
async def test_feature_flag_route_decorator_sync_and_async():
    """Verify @feature_flag_route decorator for both sync and async FastAPI handlers."""
    from unittest.mock import MagicMock

    from fastapi import HTTPException, Request
    from rodi import Container

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_fastapi.infra.decorators import feature_flag_route

    # 1. Sync endpoint with request having container
    flags = InMemoryFeatureFlagAdapter(
        {"api.beta_feature": False, "api.active_feature": True}
    )
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)

    mock_request = MagicMock(spec=Request)
    mock_request.app.state.container = container

    @feature_flag_route("api.beta_feature", default=True)
    def sync_gated_handler(request: Request) -> str:
        return "sync-allowed"

    @feature_flag_route("api.active_feature", default=False)
    def sync_active_handler(request: Request) -> str:
        return "sync-active-allowed"

    assert sync_active_handler(request=mock_request) == "sync-active-allowed"
    with pytest.raises(HTTPException) as exc_info:
        sync_gated_handler(request=mock_request)
    assert exc_info.value.status_code == 404

    # 2. Async endpoint with request having container
    @feature_flag_route("api.beta_feature", status_code=403, detail="Custom Denied")
    async def async_gated_handler(request: Request) -> str:
        return "async-allowed"

    @feature_flag_route("api.active_feature")
    async def async_active_handler(request: Request) -> str:
        return "async-active-allowed"

    assert await async_active_handler(request=mock_request) == "async-active-allowed"
    with pytest.raises(HTTPException) as exc_async_info:
        await async_gated_handler(request=mock_request)
    assert exc_async_info.value.status_code == 403
    assert exc_async_info.value.detail == "Custom Denied"

    # 3. Fallback without request in kwargs
    @feature_flag_route("api.nonexistent_feature", default=False)
    def no_req_handler() -> str:
        return "no-req-ok"

    with pytest.raises(HTTPException):
        no_req_handler()


@pytest.mark.anyio
async def test_feature_flag_route_decorator_async_fallback_no_req():
    """Verify @feature_flag_route async wrapper without request in kwargs uses ConfigFeatureFlagAdapter."""
    from fastapi import HTTPException

    from hexastack_fastapi.infra.decorators import feature_flag_route

    @feature_flag_route("api.async_unconfigured_feature", default=False)
    async def async_no_req_handler():
        return "async-val"

    with pytest.raises(HTTPException):
        await async_no_req_handler()

    @feature_flag_route("api.async_unconfigured_feature", default=True)
    async def async_allowed_handler():
        return "async-val-ok"

    assert await async_allowed_handler() == "async-val-ok"
