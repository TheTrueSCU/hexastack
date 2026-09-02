from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from hexastack_core.adapters.ratelimit import InMemoryRateLimiter
from hexastack_core.ports.ratelimit import RateLimiterPort
from hexastack_core.utils.context import UserContext, set_user_context
from hexastack_fastapi.adapters.app import create_fastapi_app
from hexastack_fastapi.adapters.ratelimit import (
    SlowapiRateLimiterAdapter,
    get_remote_address,
    get_user_or_ip_key,
    rate_limit,
)
from hexastack_fastapi.infra.config import HexastackFastApiConfig, RateLimitConfig


def test_get_remote_address_and_user_key():
    app = FastAPI()
    # 1. Forwarded for header
    req = Request(
        scope={
            "type": "http",
            "app": app,
            "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18")],
        }
    )
    assert get_remote_address(req) == "203.0.113.195"

    # 2. Client host
    req_client = Request(
        scope={
            "type": "http",
            "app": app,
            "headers": [],
            "client": ("198.51.100.1", 1234),
        }
    )
    assert get_remote_address(req_client) == "198.51.100.1"

    # 3. UserContext user_id extraction
    set_user_context(UserContext(user_id="usr_admin", tenant_id="tenant_x"))
    assert get_user_or_ip_key(req) == "user:usr_admin"

    set_user_context(UserContext(user_id="", tenant_id="tenant_y"))
    assert get_user_or_ip_key(req) == "tenant:tenant_y"

    set_user_context(None)
    assert get_user_or_ip_key(req) == "ip:203.0.113.195"


def test_slowapi_rate_limiter_adapter_crud():
    adapter = SlowapiRateLimiterAdapter(storage_uri="memory://")

    key = "test_ip_1"
    limit = "2/minute"

    assert adapter.hit(key, limit) is True
    assert adapter.hit(key, limit) is True
    # 3rd hit exceeds
    assert adapter.hit(key, limit) is False
    assert adapter.get_reset_window(key, limit) >= 1

    adapter.clear(key)
    assert adapter.hit(key, limit) is True


def test_rate_limit_decorator_sync_and_async():
    app = FastAPI()
    limiter = InMemoryRateLimiter()
    app.state.rate_limiter = limiter

    @app.get("/sync-limited")
    @rate_limit("2/minute")
    def sync_endpoint(request: Request):
        return {"ok": True}

    @app.get("/async-limited")
    @rate_limit("2/minute")
    async def async_endpoint(request: Request):
        return {"async_ok": True}

    client = TestClient(app)

    # Sync endpoint 2 allowed, 3rd fails
    res1 = client.get("/sync-limited")
    assert res1.status_code == 200
    res2 = client.get("/sync-limited")
    assert res2.status_code == 200
    res3 = client.get("/sync-limited")
    assert res3.status_code == 429
    assert "Retry-After" in res3.headers
    assert res3.json()["detail"] == "Rate limit exceeded: 2/minute."

    # Async endpoint
    res_a1 = client.get("/async-limited")
    assert res_a1.status_code == 200
    res_a2 = client.get("/async-limited")
    assert res_a2.status_code == 200
    res_a3 = client.get("/async-limited")
    assert res_a3.status_code == 429
    assert "Retry-After" in res_a3.headers


def test_create_fastapi_app_with_rate_limiting():
    config = HexastackFastApiConfig(
        ratelimit=RateLimitConfig(
            enable=True,
            default_limits=["10/minute"],
            storage_uri="memory://",
        )
    )
    app = create_fastapi_app(config=config)
    assert hasattr(app.state, "rate_limiter")
    assert isinstance(app.state.rate_limiter, RateLimiterPort)


def test_require_rate_limit_dependency_and_cqrs_router():
    from hexastack_core.domain import Command
    from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
    from hexastack_cqrs.infra.pipeline import ExecutionPipeline
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.handler import HandlerRegistry
    from hexastack_fastapi.adapters.routing import CqrsRouter

    class TestCmd(Command):
        msg: str

    handler_reg = HandlerRegistry()
    handler_reg.register(TestCmd, lambda cmd: f"echo {cmd.msg}")

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        command_registry=CommandRegistry(),
        handler_registry=handler_reg,
    )

    router = CqrsRouter()
    router.add_command("/cmd-limited", TestCmd, rate_limit="1/minute")

    app = FastAPI()
    app.state.pipeline = pipeline
    app.state.rate_limiter = InMemoryRateLimiter()
    app.include_router(router)

    client = TestClient(app)

    # 1st request succeeds
    r1 = client.post("/cmd-limited", json={"msg": "hello"})
    assert r1.status_code == 200
    assert r1.json() == "echo hello"

    # 2nd request exceeds 1/minute quota -> 429
    r2 = client.post("/cmd-limited", json={"msg": "hello"})
    assert r2.status_code == 429
    assert "Retry-After" in r2.headers
