"""Unit tests verifying infrastructure bootstrapper, config, and driving HTTP endpoints."""

from __future__ import annotations

from decimal import Decimal
from fastapi import FastAPI
import pytest
from starlette.testclient import TestClient

from financial_ledger.adapters.driven.database import (
    InMemoryAccountRepository,
    InMemoryLedgerRepository,
)
from financial_ledger.domain.commands import (
    CreateAccountCommand,
    FreezeAccountCommand,
    GetAccountBalanceQuery,
    ListLedgerEntriesQuery,
    PostingLineDto,
    RecordTransactionCommand,
    TransferMoneyCommand,
)
from financial_ledger.domain.exceptions import (
    AccountNotFoundError,
    InvalidAmountError,
)
from financial_ledger.domain.models import (
    Account,
    EntryDirection,
    JournalTransaction,
    TransactionEntry,
)
from financial_ledger.infra.bootstrap import create_app
from financial_ledger.infra.config import AppConfig
from financial_ledger.infra.handlers import (
    CreateAccountHandler,
    FreezeAccountHandler,
    GetAccountBalanceHandler,
    RecordTransactionHandler,
    TransferMoneyHandler,
)
from financial_ledger.ports.repositories import (
    AccountRepositoryPort,
    LedgerRepositoryPort,
)


def test_app_config():
    """Verify application configuration defaults."""
    config = AppConfig()
    assert config.service_name == "financial-ledger"
    assert config.environment == "development"


def test_bootstrap_create_app():
    """Verify full container bootstrapping."""
    app_result = create_app()
    assert app_result is not None
    container = app_result.container
    account_repo = container.resolve(AccountRepositoryPort)
    ledger_repo = container.resolve(LedgerRepositoryPort)
    assert account_repo is not None
    assert ledger_repo is not None

    # Test list_all on repo
    assert account_repo.list_all() == []
    acc = Account(account_id="test-1", balance=Decimal("100.00"))
    account_repo.save(acc)
    assert len(account_repo.list_all()) == 1
    assert account_repo.get_by_id("non-existent") is None

    # Test get_transaction on ledger_repo
    assert ledger_repo.get_transaction("non-existent") is None
    entry = TransactionEntry(
        account_id="test-1", direction=EntryDirection.DEBIT, amount=Decimal("10.00")
    )
    entry2 = TransactionEntry(
        account_id="test-2", direction=EntryDirection.CREDIT, amount=Decimal("10.00")
    )
    tx = JournalTransaction(
        reference="TX-T1", description="test", entries=[entry, entry2]
    )
    ledger_repo.save_transaction(tx)
    assert ledger_repo.get_transaction(tx.transaction_id) is not None


def test_error_branches_in_handlers(
    account_repo: InMemoryAccountRepository,
    ledger_repo: InMemoryLedgerRepository,
):
    """Verify validation and not-found error handling in CQRS handlers."""
    freeze_handler = FreezeAccountHandler(account_repo=account_repo)
    bal_handler = GetAccountBalanceHandler(account_repo=account_repo)
    transfer_handler = TransferMoneyHandler(
        account_repo=account_repo, ledger_repo=ledger_repo
    )
    create_handler = CreateAccountHandler(account_repo=account_repo)
    record_handler = RecordTransactionHandler(
        account_repo=account_repo, ledger_repo=ledger_repo
    )

    # Freeze non-existent account
    with pytest.raises(AccountNotFoundError):
        freeze_handler(FreezeAccountCommand(account_id="missing"))

    # Balance query for non-existent account
    with pytest.raises(AccountNotFoundError):
        bal_handler(GetAccountBalanceQuery(account_id="missing"))

    # Transfer with non-positive amount
    with pytest.raises(InvalidAmountError):
        transfer_handler(
            TransferMoneyCommand(
                source_account_id="acc-1",
                destination_account_id="acc-2",
                amount=Decimal("0.00"),
                reference="BAD-AMT",
            )
        )

    # Transfer between identical accounts
    with pytest.raises(InvalidAmountError):
        transfer_handler(
            TransferMoneyCommand(
                source_account_id="acc-1",
                destination_account_id="acc-1",
                amount=Decimal("10.00"),
                reference="SAME-ACC",
            )
        )

    # Transfer with missing source
    with pytest.raises(AccountNotFoundError, match="Source account"):
        transfer_handler(
            TransferMoneyCommand(
                source_account_id="missing-src",
                destination_account_id="acc-2",
                amount=Decimal("10.00"),
                reference="NO-SRC",
            )
        )

    # Transfer with missing dest
    create_handler(
        CreateAccountCommand(account_id="src-only", initial_balance=Decimal("50.00"))
    )
    with pytest.raises(AccountNotFoundError, match="Destination account"):
        transfer_handler(
            TransferMoneyCommand(
                source_account_id="src-only",
                destination_account_id="missing-dst",
                amount=Decimal("10.00"),
                reference="NO-DST",
            )
        )

    # RecordTransaction with missing account
    with pytest.raises(AccountNotFoundError):
        record_handler(
            RecordTransactionCommand(
                reference="SPLIT-ERR",
                description="Error test",
                entries=[
                    PostingLineDto(
                        account_id="missing-1",
                        direction="DEBIT",
                        amount=Decimal("10.00"),
                    ),
                    PostingLineDto(
                        account_id="missing-2",
                        direction="CREDIT",
                        amount=Decimal("10.00"),
                    ),
                ],
            )
        )


def test_fastapi_rest_endpoints():
    """Verify driving FastAPI REST endpoints end-to-end."""
    app_result = create_app()
    fastapi_app = app_result.container.resolve(FastAPI)
    assert fastapi_app is not None

    client = TestClient(fastapi_app)

    # 1. Create source account
    res1 = client.post(
        "/accounts",
        json={
            "account_id": "acc-rest-src",
            "initial_balance": 500.0,
            "currency": "USD",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["account_id"] == "acc-rest-src"

    # 2. Create destination account
    res2 = client.post(
        "/accounts",
        json={
            "account_id": "acc-rest-dst",
            "initial_balance": 100.0,
            "currency": "USD",
        },
    )
    assert res2.status_code == 201

    # Duplicate account returns 409
    res_dup = client.post(
        "/accounts", json={"account_id": "acc-rest-src", "initial_balance": 500.0}
    )
    assert res_dup.status_code == 409

    # 3. Transfer money
    res3 = client.post(
        "/transfers",
        json={
            "source_account_id": "acc-rest-src",
            "destination_account_id": "acc-rest-dst",
            "amount": 150.0,
            "reference": "REST-TX-01",
            "description": "API transfer test",
        },
    )
    assert res3.status_code == 200
    data = res3.json()
    assert float(data["source_balance"]) == 350.0
    assert float(data["destination_balance"]) == 250.0

    # 4. Get balance
    res4 = client.get("/accounts/acc-rest-src/balance")
    assert res4.status_code == 200
    assert float(res4.json()["balance"]) == 350.0

    # Balance 404
    res4_404 = client.get("/accounts/acc-missing/balance")
    assert res4_404.status_code == 404

    # 5. List entries
    res5 = client.get("/accounts/acc-rest-src/entries")
    assert res5.status_code == 200
    assert len(res5.json()["entries"]) == 1

    # 6. Freeze account
    res6 = client.post("/accounts/freeze", json={"account_id": "acc-rest-src"})
    assert res6.status_code == 200
    assert res6.json()["status"] == "FROZEN"

    # Freeze 404
    res6_404 = client.post("/accounts/freeze", json={"account_id": "acc-missing"})
    assert res6_404.status_code == 404

    # Transfer with frozen account returns 400
    res_frozen = client.post(
        "/transfers",
        json={
            "source_account_id": "acc-rest-src",
            "destination_account_id": "acc-rest-dst",
            "amount": 10.0,
            "reference": "REST-FROZEN-01",
        },
    )
    assert res_frozen.status_code == 400

    # 7. Record transaction via REST
    res7 = client.post(
        "/transactions",
        json={
            "reference": "REST-SPLIT-01",
            "description": "Split REST test",
            "entries": [
                {"account_id": "acc-rest-dst", "direction": "DEBIT", "amount": 50.0},
                {"account_id": "acc-rest-src", "direction": "CREDIT", "amount": 50.0},
            ],
        },
    )
    # Will fail with 400 because acc-rest-src is frozen
    assert res7.status_code == 400
