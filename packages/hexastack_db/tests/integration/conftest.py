from collections.abc import Generator

import pytest

from hexastack_core.utils.imports import optional_dependency


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str]:
    """Ephemeral PostgreSQL database container URL for zero-mock integration testing.

    Notes/Architectural Intent:
        Spawns a real PostgreSQL 16 container using testcontainers if Docker and testcontainers
        are installed and active. If unavailable (e.g. lightweight local unit runner),
        falls back to in-memory SQLite with full schema creation.
    """
    has_docker = False
    docker_module = optional_dependency("docker")
    tc_pg = optional_dependency("testcontainers.postgres")

    if docker_module is not None and tc_pg is not None:
        try:
            client = docker_module.from_env()
            client.ping()
            has_docker = True
        except Exception:
            has_docker = False

    if has_docker and tc_pg is not None:
        container = tc_pg.PostgresContainer("postgres:16-alpine")
        with container as postgres:
            yield postgres.get_connection_url()
    else:
        yield "sqlite:///:memory:"
