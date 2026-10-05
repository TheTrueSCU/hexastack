from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.utils.context import (
    correlation_id_ctx,
    set_correlation_id,
)
from hexastack_fastapi.adapters.health import create_health_router
from hexastack_fastapi.infra.config import HealthConfig
from hexastack_fastapi.infra.middleware.correlation import (
    CorrelationHttpMiddleware,
)


def test_custom_health_paths():
    cfg = HealthConfig(health_path="/livez", ready_path="/readyz")
    app = FastAPI()
    app.include_router(create_health_router(config=cfg))

    client = TestClient(app)
    assert client.get("/livez").status_code == 200


def test_health_and_readiness_endpoints_healthy():
    container = Container()
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware)
    router = create_health_router(container=container)
    assert "Health" in router.tags
    app.include_router(router)

    corr_token = set_correlation_id("test-corr-health-123")

    client = TestClient(app)

    # 1. Health (Liveness)
    h_res = client.get("/health", headers={"X-Correlation-ID": "test-corr-health-123"})
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "ok"
    assert "timestamp" in h_data
    assert h_data["correlation_id"] == "test-corr-health-123"

    # 2. Readiness
    r_res = client.get("/ready")
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert r_data["status"] == "ready"
    assert r_data["checks"]["container"] == "ok"

    correlation_id_ctx.reset(corr_token)


def test_readiness_unconfigured_container():
    app = FastAPI()
    app.include_router(create_health_router(container=None))

    client = TestClient(app)
    r_res = client.get("/ready")
    assert r_res.status_code == 503
    r_data = r_res.json()
    assert r_data["status"] == "unhealthy"
    assert r_data["checks"]["container"] == "unconfigured"
