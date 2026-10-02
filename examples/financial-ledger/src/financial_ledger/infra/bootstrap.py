"""Hexastack bootstrapper and application kernel assembly for financial ledger."""

from __future__ import annotations

from fastapi import FastAPI
from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
from rodi import Container

import financial_ledger.adapters.driving.cli
import financial_ledger.infra.handlers
from financial_ledger.adapters.driven.database import (
    InMemoryAccountRepository,
    InMemoryLedgerRepository,
)
from financial_ledger.adapters.driving.http import router
from financial_ledger.ports.repositories import (
    AccountRepositoryPort,
    LedgerRepositoryPort,
)

__all__ = [
    "create_app",
]


def create_app() -> BootstrapResult:
    """Bootstrap full Hexastack microservice kernel."""
    di = Container()
    account_repo = InMemoryAccountRepository()
    ledger_repo = InMemoryLedgerRepository()
    di.add_instance(account_repo, declared_class=AccountRepositoryPort)
    di.add_instance(ledger_repo, declared_class=LedgerRepositoryPort)

    result = bootstrap(
        container=di,
        packages_to_scan=[
            financial_ledger.adapters.driving.cli,
            financial_ledger.infra.handlers,
        ],
    )
    app = result.container.resolve(FastAPI)
    app.include_router(router)
    return result
