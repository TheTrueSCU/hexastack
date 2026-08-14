from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexastack_core.utils.context import (
    get_correlation_id,
    get_user_context,
)
from hexastack_fastapi.infra.config import HexastackFastApiConfig
from hexastack_fastapi.infra.middleware.correlation import (
    CorrelationHttpMiddleware,
)


def create_test_app(config: HexastackFastApiConfig | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware, config=config)

    @app.get("/ping")
    async def ping():
        cid = get_correlation_id()
        user = get_user_context()
        return {
            "message": "pong",
            "correlation_id": cid,
            "user_id": user.user_id if user else None,
            "tenant_id": user.tenant_id if user else None,
        }

    return app


def test_correlation_middleware_generated_id():
    app = create_test_app()
    client = TestClient(app)

    response = client.get("/ping")
    assert response.status_code == 200
    cid_header = response.headers.get("x-correlation-id")
    assert cid_header is not None
    data = response.json()
    assert data["correlation_id"] == cid_header


def test_correlation_middleware_propagated_id():
    app = create_test_app()
    client = TestClient(app)

    custom_cid = "custom-test-cid-12345"
    response = client.get("/ping", headers={"X-Correlation-ID": custom_cid})
    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == custom_cid
    data = response.json()
    assert data["correlation_id"] == custom_cid


def test_correlation_middleware_user_context():
    app = create_test_app()
    client = TestClient(app)

    headers = {
        "X-Correlation-ID": "corr-999",
        "X-User-ID": "user-alice",
        "X-Tenant-ID": "tenant-acme",
    }
    response = client.get("/ping", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["correlation_id"] == "corr-999"
    assert data["user_id"] == "user-alice"
    assert data["tenant_id"] == "tenant-acme"
