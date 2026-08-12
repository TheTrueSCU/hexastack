from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_fastapi.adapters.db_session import (
    AsyncDbSessionMiddleware,
    DbSessionMiddleware,
    add_db_session_middleware,
)
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


def _sync_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return sessionmaker(bind=engine)


def _async_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    return async_sessionmaker(bind=engine)


def test_db_session_middleware_injects_session():
    app = FastAPI()
    factory = _sync_factory()
    app.add_middleware(DbSessionMiddleware, session_factory=factory)

    @app.get("/check")
    async def check(request: Request):
        return {"has_session": hasattr(request.state, "db_session")}

    client = TestClient(app)
    response = client.get("/check")
    assert response.status_code == 200
    assert response.json()["has_session"] is True


def test_async_db_session_middleware_injects_session():
    app = FastAPI()
    factory = _async_factory()
    app.add_middleware(AsyncDbSessionMiddleware, session_factory=factory)

    @app.get("/check")
    async def check(request: Request):
        return {"has_session": hasattr(request.state, "db_session")}

    client = TestClient(app)
    response = client.get("/check")
    assert response.status_code == 200
    assert response.json()["has_session"] is True


def test_add_db_session_middleware_sync():
    app = FastAPI()
    factory = _sync_factory()
    add_db_session_middleware(app, factory, async_mode=False)

    @app.get("/check")
    async def check(request: Request):
        return {"has_session": hasattr(request.state, "db_session")}

    client = TestClient(app)
    assert client.get("/check").json()["has_session"] is True


def test_add_db_session_middleware_async():
    app = FastAPI()
    factory = _async_factory()
    add_db_session_middleware(app, factory, async_mode=True)

    @app.get("/check")
    async def check(request: Request):
        return {"has_session": hasattr(request.state, "db_session")}

    client = TestClient(app)
    assert client.get("/check").json()["has_session"] is True


def test_session_closed_after_response():
    """Session's close() must be called even when response completes normally."""
    closed: list[bool] = []

    class _TrackingSession:
        def close(self) -> None:
            closed.append(True)

    class TrackingFactory:
        def __call__(self) -> _TrackingSession:
            return _TrackingSession()

    app = FastAPI()
    app.add_middleware(DbSessionMiddleware, session_factory=TrackingFactory())

    @app.get("/track")
    async def track(request: Request):
        return {"ok": True}

    client = TestClient(app)
    client.get("/track")
    assert closed == [True]
