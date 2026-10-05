"""Property-based negative API fuzz testing with Schemathesis."""

from typing import Any

import schemathesis
from fastapi import FastAPI
from rodi import Container
from schemathesis import Case

from hexastack_core.domain import Command, Generic, Query
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


class FuzzCreateAccount(Command):
    account_id: str
    email: str
    initial_balance: float = 0.0


class FuzzGetAccount(Query):
    account_id: str


class FuzzAccountDTO(Generic):
    account_id: str
    email: str
    balance: float


def _build_fuzz_app() -> FastAPI:
    handler_reg = HandlerRegistry()
    presenter_reg = PresenterRegistry()

    accounts: dict[str, FuzzAccountDTO] = {}

    def handle_create(cmd: FuzzCreateAccount) -> FuzzAccountDTO:
        dto = FuzzAccountDTO(
            account_id=cmd.account_id,
            email=cmd.email,
            balance=cmd.initial_balance,
        )
        accounts[cmd.account_id] = dto
        return dto

    def handle_get(qry: FuzzGetAccount) -> FuzzAccountDTO:
        if qry.account_id in accounts:
            return accounts[qry.account_id]
        return FuzzAccountDTO(
            account_id=qry.account_id, email="unknown@example.com", balance=0.0
        )

    handler_reg.register(FuzzCreateAccount, handle_create)
    handler_reg.register(FuzzGetAccount, handle_get)

    class AccountJsonPresenter(PresenterPort):
        def present(self, instance: Generic) -> Any:
            if isinstance(instance, FuzzAccountDTO):
                return {
                    "account_id": instance.account_id,
                    "email": instance.email,
                    "balance": instance.balance,
                }
            return None

    presenter_reg.register(FuzzAccountDTO, "json", AccountJsonPresenter())

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    router = CqrsRouter(prefix="/api/v1")
    router.add_command(
        "/accounts",
        FuzzCreateAccount,
        method="POST",
        status_code=201,
        output_format="json",
    )
    router.add_query(
        "/accounts/{account_id}", FuzzGetAccount, method="GET", output_format="json"
    )

    app = FastAPI(title="Fuzz App")
    app.state.container = Container()
    app.state.pipeline = pipeline
    app.include_router(router)
    return app


_fuzz_app = _build_fuzz_app()
schema = schemathesis.openapi.from_asgi("/openapi.json", _fuzz_app)


@schema.parametrize()
def test_api_negative_fuzzing_no_500s(case: Case) -> None:
    """Schemathesis negative property fuzzing.

    Invariants Proven:
        Under arbitrary generated inputs (invalid types, boundary numbers,
        oversized payloads, non-ASCII Unicode), the application must never
        crash with an unhandled 500 Internal Server Error.
    """
    response = case.call()
    assert response.status_code < 500
