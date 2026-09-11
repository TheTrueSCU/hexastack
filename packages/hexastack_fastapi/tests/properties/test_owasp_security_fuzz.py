"""Adversarial OWASP API Security Fuzzing (SQLi, Command Injection, BOLA, Mass Assignment).

Notes/Architectural Intent:
    Fuzzes FastAPI CQRS endpoints against OWASP Top 10 adversarial vectors:
    1. SQL Injection (SQLi) payloads
    2. OS Command Injection payloads
    3. Path Traversal & LFI sequences
    4. Mass Assignment & Parameter Pollution
    5. Broken Object Level Authorization (BOLA) ID manipulation
    Proves that the framework fails closed, never crashes with unhandled 500 errors,
    strips unauthorized fields, and respects object-level authorization boundaries.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import Field
from rodi import Container

from hexastack_core.domain import Command, Generic, Query
from hexastack_core.domain.exceptions import NotFoundError
from hexastack_core.ports.presenter import PresenterPort
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.adapters.routing import CqrsRouter
from hexastack_fastapi.infra.exception_handlers import register_exception_handlers


# Domain Commands and Queries
class SecureCreateUserCommand(Command):
    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=128)
    role: str = Field(default="user")


class SecureGetUserQuery(Query):
    tenant_id: str
    user_id: str


class SecureUserDTO(Generic):
    user_id: str
    username: str
    email: str
    role: str
    tenant_id: str


class UserJsonPresenter(PresenterPort):
    def present(self, instance: Generic) -> Any:
        if isinstance(instance, SecureUserDTO):
            return {
                "user_id": instance.user_id,
                "username": instance.username,
                "email": instance.email,
                "role": instance.role,
                "tenant_id": instance.tenant_id,
            }
        return None


def _build_security_test_app() -> tuple[FastAPI, dict[str, SecureUserDTO]]:
    """Build a test FastAPI CQRS application with in-memory state and tenant isolation."""
    users_db: dict[str, SecureUserDTO] = {
        "user_tenant_1": SecureUserDTO(
            user_id="user_tenant_1",
            username="alice",
            email="alice@company1.com",
            role="user",
            tenant_id="tenant_1",
        ),
        "user_tenant_2": SecureUserDTO(
            user_id="user_tenant_2",
            username="bob",
            email="bob@company2.com",
            role="user",
            tenant_id="tenant_2",
        ),
    }

    handler_reg = HandlerRegistry()
    presenter_reg = PresenterRegistry()

    def handle_create_user(cmd: SecureCreateUserCommand) -> SecureUserDTO:
        # Enforce business invariant: role cannot be escalated via user input
        safe_role = "user" if cmd.role != "user" else "user"
        user_id = f"user_{len(users_db) + 1}"
        dto = SecureUserDTO(
            user_id=user_id,
            username=cmd.username,
            email=cmd.email,
            role=safe_role,
            tenant_id="tenant_1",
        )
        users_db[user_id] = dto
        return dto

    def handle_get_user(qry: SecureGetUserQuery) -> SecureUserDTO:
        user = users_db.get(qry.user_id)
        if not user or user.tenant_id != qry.tenant_id:
            raise NotFoundError(
                f"User {qry.user_id} not found in tenant {qry.tenant_id}"
            )
        return user

    handler_reg.register(SecureCreateUserCommand, handle_create_user)
    handler_reg.register(SecureGetUserQuery, handle_get_user)
    presenter_reg.register(SecureUserDTO, "json", UserJsonPresenter())

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    router = CqrsRouter(prefix="/api/security")
    router.add_command(
        "/users",
        SecureCreateUserCommand,
        method="POST",
        status_code=201,
        output_format="json",
    )
    router.add_query(
        "/tenants/{tenant_id}/users/{user_id}",
        SecureGetUserQuery,
        method="GET",
        output_format="json",
    )

    app = FastAPI(title="OWASP Security Fuzz App")
    app.state.container = Container()
    app.state.pipeline = pipeline
    register_exception_handlers(app)
    app.include_router(router)
    return app, users_db


_app, _db = _build_security_test_app()
_client = TestClient(_app, raise_server_exceptions=False)


# Adversarial payload corpus
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "admin' --",
    "1; DROP TABLE users; --",
    "' UNION SELECT null, username, password FROM users --",
    "1' AND SLEEP(5) AND '1'='1",
    "1' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT(version(), FLOOR(RAND(0)*2)) x FROM information_schema.tables GROUP BY x) a) --",
]

COMMAND_INJECTION_PAYLOADS = [
    "; cat /etc/passwd",
    "| id",
    "$(whoami)",
    "`ls -la`",
    "& ping -c 1 127.0.0.1 &",
    "|| echo 'PWNED'",
    "\n/bin/sh -i\n",
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../../etc/passwd",
    "..\\..\\..\\..\\windows\\win.ini",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "..%252f..%252f..%252fetc%252fpasswd",
    "/etc/shadow\x00.png",
    "....//....//etc/passwd",
]


@given(
    payload=st.sampled_from(
        SQLI_PAYLOADS + COMMAND_INJECTION_PAYLOADS + PATH_TRAVERSAL_PAYLOADS
    ),
    target_field=st.sampled_from(["username", "email"]),
)
def test_adversarial_sqli_and_command_injection_fuzzing(
    payload: str, target_field: str
) -> None:
    """Invariant: Injection payloads in command bodies never cause unhandled 500 crashes."""
    body: dict[str, Any] = {
        "username": "legit_user",
        "email": "user@example.com",
    }
    body[target_field] = payload

    response = _client.post("/api/security/users", json=body)
    # Server must either reject with 422 (validation error) or accept with 201 (safely serialized)
    # It must NEVER crash with 500
    assert response.status_code in (201, 400, 422)
    assert response.status_code < 500


@given(
    malicious_id=st.sampled_from(PATH_TRAVERSAL_PAYLOADS + SQLI_PAYLOADS),
)
def test_adversarial_path_traversal_and_sqli_in_url_fuzzing(malicious_id: str) -> None:
    """Invariant: Path traversal / SQLi sequences in path parameters never cause 500 crashes."""
    encoded_id = quote(malicious_id, safe="")
    response = _client.get(f"/api/security/tenants/tenant_1/users/{encoded_id}")
    # Must be 404 Not Found, 422, or 400. Never 500.
    assert response.status_code in (200, 400, 404, 422)
    assert response.status_code < 500


@given(
    injected_key=st.sampled_from(
        ["is_admin", "is_superuser", "role", "permissions", "balance", "credit_limit"]
    ),
    injected_val=st.sampled_from([True, "admin", "root", 999999, ["all"]]),
)
def test_mass_assignment_parameter_pollution_invariant(
    injected_key: str, injected_val: Any
) -> None:
    """Invariant: Mass assignment / parameter pollution fails closed without privilege escalation."""
    body = {
        "username": "charlie",
        "email": "charlie@example.com",
        injected_key: injected_val,
    }

    response = _client.post("/api/security/users", json=body)
    assert response.status_code in (201, 422)
    assert response.status_code < 500

    if response.status_code == 201:
        data = response.json()
        # Ensure unauthorized elevated role was NOT granted
        assert data.get("role") != "admin"
        assert data.get("role") != "root"
        assert "is_admin" not in data
        assert "permissions" not in data


@given(
    attacker_tenant=st.sampled_from(["tenant_1", "tenant_3", "attacker_tenant"]),
    victim_user_id=st.sampled_from(["user_tenant_2"]),  # Belongs to tenant_2
)
@settings(max_examples=25)
def test_bola_cross_tenant_access_control_invariant(
    attacker_tenant: str, victim_user_id: str
) -> None:
    """Invariant: BOLA / IDOR attempts across tenant boundaries fail closed and never leak victim data."""
    response = _client.get(
        f"/api/security/tenants/{attacker_tenant}/users/{victim_user_id}"
    )
    # Since victim belongs to tenant_2, requests from tenant_1 or attacker_tenant must fail closed with 404
    assert response.status_code in (403, 404, 422)
    assert response.status_code < 500


__all__ = [
    "test_adversarial_path_traversal_and_sqli_in_url_fuzzing",
    "test_adversarial_sqli_and_command_injection_fuzzing",
    "test_bola_cross_tenant_access_control_invariant",
    "test_mass_assignment_parameter_pollution_invariant",
]
