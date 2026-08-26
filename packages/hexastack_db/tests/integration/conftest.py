import importlib
import importlib.util
from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str]:
    """Ephemeral PostgreSQL database container URL for zero-mock integration testing.

    Notes/Architectural Intent:
        Spawns a real PostgreSQL 16 container using testcontainers if Docker and testcontainers
        are installed and active. If unavailable (e.g. lightweight local unit runner),
        falls back to in-memory SQLite with full schema creation.
    """
    has_docker = False
    spec_tc = importlib.util.find_spec("testcontainers")
    spec_dk = importlib.util.find_spec("docker")
    if spec_tc is not None and spec_dk is not None:
        try:
            docker_module = importlib.import_module("docker")
            client = docker_module.from_env()
            client.ping()
            has_docker = True
        except Exception:
            has_docker = False

    if has_docker:
        tc_pg: Any = importlib.import_module("testcontainers.postgres")
        container = tc_pg.PostgresContainer("postgres:16-alpine")
        with container as postgres:
            yield postgres.get_connection_url()
    else:
        yield "sqlite:///:memory:"
