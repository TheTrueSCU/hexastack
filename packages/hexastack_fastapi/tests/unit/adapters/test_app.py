from fastapi.testclient import TestClient
from hexastack_core.adapters.logging.in_memory import InMemoryLogger
from hexastack_core.ports.logging import LoggingPort
from hexastack_fastapi.adapters.app import create_fastapi_app
from hexastack_fastapi.infra.config import (
    CorsConfig,
    HexastackFastApiConfig,
)
from rodi import Container


def test_create_fastapi_app_defaults():
    container = Container()
    app = create_fastapi_app(container=container)

    assert app.title == "Hexastack API"
    assert app.state.container is container

    client = TestClient(app)
    res = client.get("/docs")
    assert res.status_code == 200

    # Default health check route should be mounted
    health_res = client.get("/health")
    assert health_res.status_code == 200


def test_create_fastapi_app_with_cors():
    cfg = HexastackFastApiConfig(
        title="Custom CORS App",
        cors=CorsConfig(enable=True, allow_origins=["https://myapp.com"]),
    )
    app = create_fastapi_app(config=cfg)

    @app.get("/hello")
    async def hello():
        return {"msg": "hello"}

    client = TestClient(app)
    res = client.options(
        "/hello",
        headers={
            "Origin": "https://myapp.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://myapp.com"


def test_create_fastapi_app_lifespan_logger_close():
    class ClosableLogger(InMemoryLogger):
        def __init__(self):
            super().__init__()
            self.closed = False

        def close(self):
            self.closed = True

    closable = ClosableLogger()
    container = Container()
    container.add_instance(closable, declared_class=LoggingPort)

    app = create_fastapi_app(container=container)

    with TestClient(app):
        assert closable.closed is False

    # After client exits, lifespan should close logger
    assert closable.closed is True
