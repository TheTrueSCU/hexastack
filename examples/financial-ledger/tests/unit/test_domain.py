"""Unit tests verifying double-entry domain models and CQRS handlers."""

from __future__ import annotations

from decimal import Decimal
import pytest

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
    AccountAlreadyExistsError,
    AccountFrozenError,
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    UnbalancedTransactionError,
)
from financial_ledger.domain.models import (
    Account,
    EntryDirection,
    JournalTransaction,
    TransactionEntry,
)
from financial_ledger.infra.handlers import (
    CreateAccountHandler,
    FreezeAccountHandler,
    GetAccountBalanceHandler,
    ListLedgerEntriesHandler,
    RecordTransactionHandler,
    TransferMoneyHandler,
)


def test_double_entry_balance_invariant():
    """Verify that unbalanced transactions are strictly rejected."""
    # Balanced transaction
    entries = [
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=Decimal("50.00")),
        TransactionEntry(account_id="acc-2", direction=EntryDirection.CREDIT, amount=Decimal("50.00")),
    ]
    tx = JournalTransaction(reference="TX-001", description="Valid transfer", entries=entries)
    assert tx.reference == "TX-001"
    assert len(tx.entries) == 2

    # Unbalanced transaction (debit 50 != credit 40)
    bad_entries = [
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=Decimal("50.00")),
        TransactionEntry(account_id="acc-2", direction=EntryDirection.CREDIT, amount=Decimal("40.00")),
    ]
    with pytest.raises(UnbalancedTransactionError, match="total debits"):
        JournalTransaction(reference="TX-BAD", description="Unbalanced", entries=bad_entries)

    # Less than 2 entries
    single_entry = [
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=Decimal("50.00")),
    ]
    with pytest.raises(UnbalancedTransactionError, match="at least two"):
        JournalTransaction(reference="TX-SINGLE", description="Single leg", entries=single_entry)


def test_invalid_entry_amount():
    """Verify non-positive amounts are rejected."""
    with pytest.raises(InvalidAmountError):
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=Decimal("0.00"))

    with pytest.raises(InvalidAmountError):
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=Decimal("-10.00"))


def test_account_creation_and_balance_query(account_repo: InMemoryAccountRepository):
    """Verify creating an account and querying its balance."""
    handler = CreateAccountHandler(account_repo=account_repo)
    bal_handler = GetAccountBalanceHandler(account_repo=account_repo)

    cmd = CreateAccountCommand(
        account_id="acc-alice",
        tenant_id="t-1",
        owner_id="alice",
        currency="USD",
        initial_balance=Decimal("100.00"),
        credit_limit=Decimal("0.00"),
    )
    res = handler(cmd)
    assert res.account_id == "acc-alice"
    assert res.balance == Decimal("100.00")
    assert res.status == "ACTIVE"

    # Duplicate creation raises error
    with pytest.raises(AccountAlreadyExistsError):
        handler(cmd)

    # Query balance
    bal_res = bal_handler(GetAccountBalanceQuery(account_id="acc-alice"))
    assert bal_res.balance == Decimal("100.00")
    assert bal_res.status == "ACTIVE"


def test_account_freeze_prevents_transactions(
    account_repo: InMemoryAccountRepository,
    ledger_repo: InMemoryLedgerRepository,
):
    """Verify frozen account cannot send or receive transfers."""
    create_handler = CreateAccountHandler(account_repo=account_repo)
    freeze_handler = FreezeAccountHandler(account_repo=account_repo)
    transfer_handler = TransferMoneyHandler(account_repo=account_repo, ledger_repo=ledger_repo)

    create_handler(CreateAccountCommand(account_id="acc-1", initial_balance=Decimal("100.00")))
    create_handler(CreateAccountCommand(account_id="acc-2", initial_balance=Decimal("50.00")))

    freeze_res = freeze_handler(FreezeAccountCommand(account_id="acc-1"))
    assert freeze_res.status == "FROZEN"

    transfer_cmd = TransferMoneyCommand(
        source_account_id="acc-1",
        destination_account_id="acc-2",
        amount=Decimal("25.00"),
        reference="TX-FREEZE-TEST",
    )
    with pytest.raises(AccountFrozenError):
        transfer_handler(transfer_cmd)


def test_transfer_money_success_and_ledger_history(
    account_repo: InMemoryAccountRepository,
    ledger_repo: InMemoryLedgerRepository,
):
    """Verify successful double-entry transfer and ledger posting line retrieval."""
    create_handler = CreateAccountHandler(account_repo=account_repo)
    transfer_handler = TransferMoneyHandler(account_repo=account_repo, ledger_repo=ledger_repo)
    list_handler = ListLedgerEntriesHandler(ledger_repo=ledger_repo)

    create_handler(CreateAccountCommand(account_id="acc-src", initial_balance=Decimal("200.00")))
    create_handler(CreateAccountCommand(account_id="acc-dst", initial_balance=Decimal("50.00")))

    tx_res = transfer_handler(
        TransferMoneyCommand(
            source_account_id="acc-src",
            destination_account_id="acc-dst",
            amount=Decimal("75.50"),
            reference="TX-PAY-01",
            description="Payment for services",
        )
    )
    assert tx_res.source_balance == Decimal("124.50")
    assert tx_res.destination_balance == Decimal("125.50")

    # Check entries for source
    src_entries = list_handler(ListLedgerEntriesQuery(account_id="acc-src"))
    assert len(src_entries.entries) == 1
    assert src_entries.entries[0].direction == "DEBIT"
    assert src_entries.entries[0].amount == Decimal("75.50")

    # Check entries for dest
    dst_entries = list_handler(ListLedgerEntriesQuery(account_id="acc-dst"))
    assert len(dst_entries.entries) == 1
    assert dst_entries.entries[0].direction == "CREDIT"
    assert dst_entries.entries[0].amount == Decimal("75.50")


def test_transfer_insufficient_funds(
    account_repo: InMemoryAccountRepository,
    ledger_repo: InMemoryLedgerRepository,
):
    """Verify transfer fails when source balance is below required amount without credit limit."""
    create_handler = CreateAccountHandler(account_repo=account_repo)
    transfer_handler = TransferMoneyHandler(account_repo=account_repo, ledger_repo=ledger_repo)

    create_handler(CreateAccountCommand(account_id="acc-poor", initial_balance=Decimal("10.00")))
    create_handler(CreateAccountCommand(account_id="acc-rich", initial_balance=Decimal("1000.00")))

    cmd = TransferMoneyCommand(
        source_account_id="acc-poor",
        destination_account_id="acc-rich",
        amount=Decimal("50.00"),
        reference="TX-OVERDRAFT",
    )
    with pytest.raises(InsufficientFundsError):
        transfer_handler(cmd)


def test_multi_legged_record_transaction(
    account_repo: InMemoryAccountRepository,
    ledger_repo: InMemoryLedgerRepository,
):
    """Verify recording an arbitrary multi-legged split transaction (e.g. fee split)."""
    create_handler = CreateAccountHandler(account_repo=account_repo)
    record_handler = RecordTransactionHandler(account_repo=account_repo, ledger_repo=ledger_repo)

    create_handler(CreateAccountCommand(account_id="acc-payer", initial_balance=Decimal("100.00")))
    create_handler(CreateAccountCommand(account_id="acc-merchant", initial_balance=Decimal("0.00")))
    create_handler(CreateAccountCommand(account_id="acc-fee", initial_balance=Decimal("0.00")))

    cmd = RecordTransactionCommand(
        reference="TX-SPLIT-01",
        description="Purchase with 3% fee",
        entries=[
            PostingLineDto(account_id="acc-payer", direction="DEBIT", amount=Decimal("100.00")),
            PostingLineDto(account_id="acc-merchant", direction="CREDIT", amount=Decimal("97.00")),
            PostingLineDto(account_id="acc-fee", direction="CREDIT", amount=Decimal("3.00")),
        ],
    )
    res = record_handler(cmd)
    assert res.entry_count == 3

    assert account_repo.get_by_id("acc-payer").balance == Decimal("0.00")
    assert account_repo.get_by_id("acc-merchant").balance == Decimal("97.00")
    assert account_repo.get_by_id("acc-fee").balance == Decimal("3.00")
