"""CQRS command and query handlers for double-entry financial ledger."""

from __future__ import annotations

from decimal import Decimal
import uuid

from hexastack_cqrs.infra.decorators import command_handler, query_handler

from financial_ledger.domain.commands import (
    CreateAccountCommand,
    CreateAccountResponse,
    FreezeAccountCommand,
    FreezeAccountResponse,
    GetAccountBalanceQuery,
    GetAccountBalanceResponse,
    ListLedgerEntriesQuery,
    ListLedgerEntriesResponse,
    PostingLineDto,
    RecordTransactionCommand,
    RecordTransactionResponse,
    TransferMoneyCommand,
    TransferMoneyResponse,
)
from financial_ledger.domain.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAmountError,
)
from financial_ledger.domain.models import (
    Account,
    AccountStatus,
    EntryDirection,
    JournalTransaction,
    TransactionEntry,
)
from financial_ledger.ports.repositories import AccountRepositoryPort, LedgerRepositoryPort

__all__ = [
    "CreateAccountHandler",
    "FreezeAccountHandler",
    "GetAccountBalanceHandler",
    "ListLedgerEntriesHandler",
    "RecordTransactionHandler",
    "TransferMoneyHandler",
]


@command_handler(CreateAccountCommand)
class CreateAccountHandler:
    """Handler creating new accounts."""

    def __init__(self, account_repo: AccountRepositoryPort) -> None:
        self.account_repo = account_repo

    def __call__(self, cmd: CreateAccountCommand) -> CreateAccountResponse:
        acc_id = cmd.account_id or str(uuid.uuid4())
        existing = self.account_repo.get_by_id(acc_id)
        if existing is not None:
            raise AccountAlreadyExistsError(f"Account with ID '{acc_id}' already exists.")

        account = Account(
            account_id=acc_id,
            tenant_id=cmd.tenant_id,
            owner_id=cmd.owner_id,
            currency=cmd.currency,
            balance=cmd.initial_balance,
            credit_limit=cmd.credit_limit,
            status=AccountStatus.ACTIVE,
        )
        self.account_repo.save(account)
        return CreateAccountResponse(
            account_id=account.account_id,
            currency=account.currency,
            balance=account.balance,
            status=account.status.value,
        )


@command_handler(FreezeAccountCommand)
class FreezeAccountHandler:
    """Handler freezing active accounts."""

    def __init__(self, account_repo: AccountRepositoryPort) -> None:
        self.account_repo = account_repo

    def __call__(self, cmd: FreezeAccountCommand) -> FreezeAccountResponse:
        account = self.account_repo.get_by_id(cmd.account_id)
        if account is None:
            raise AccountNotFoundError(f"Account '{cmd.account_id}' not found.")

        account.status = AccountStatus.FROZEN
        self.account_repo.save(account)
        return FreezeAccountResponse(
            account_id=account.account_id,
            status=account.status.value,
        )


@command_handler(TransferMoneyCommand)
class TransferMoneyHandler:
    """Handler executing double-entry transfers."""

    def __init__(
        self,
        account_repo: AccountRepositoryPort,
        ledger_repo: LedgerRepositoryPort,
    ) -> None:
        self.account_repo = account_repo
        self.ledger_repo = ledger_repo

    def __call__(self, cmd: TransferMoneyCommand) -> TransferMoneyResponse:
        if cmd.amount <= Decimal("0.00"):
            raise InvalidAmountError(f"Transfer amount must be positive, got {cmd.amount}")

        if cmd.source_account_id == cmd.destination_account_id:
            raise InvalidAmountError("Source and destination accounts must be distinct.")

        source = self.account_repo.get_by_id(cmd.source_account_id)
        if source is None:
            raise AccountNotFoundError(f"Source account '{cmd.source_account_id}' not found.")

        dest = self.account_repo.get_by_id(cmd.destination_account_id)
        if dest is None:
            raise AccountNotFoundError(f"Destination account '{cmd.destination_account_id}' not found.")

        debit_entry = TransactionEntry(
            account_id=source.account_id,
            direction=EntryDirection.DEBIT,
            amount=cmd.amount,
            currency=cmd.currency,
        )
        credit_entry = TransactionEntry(
            account_id=dest.account_id,
            direction=EntryDirection.CREDIT,
            amount=cmd.amount,
            currency=cmd.currency,
        )

        source.apply_entry(debit_entry)
        dest.apply_entry(credit_entry)

        tx = JournalTransaction(
            reference=cmd.reference,
            description=cmd.description,
            entries=[debit_entry, credit_entry],
        )

        self.account_repo.save(source)
        self.account_repo.save(dest)
        self.ledger_repo.save_transaction(tx)

        return TransferMoneyResponse(
            transaction_id=tx.transaction_id,
            reference=tx.reference,
            source_account_id=source.account_id,
            destination_account_id=dest.account_id,
            amount=cmd.amount,
            source_balance=source.balance,
            destination_balance=dest.balance,
        )


@command_handler(RecordTransactionCommand)
class RecordTransactionHandler:
    """Handler executing arbitrary balanced journal transactions."""

    def __init__(
        self,
        account_repo: AccountRepositoryPort,
        ledger_repo: LedgerRepositoryPort,
    ) -> None:
        self.account_repo = account_repo
        self.ledger_repo = ledger_repo

    def __call__(self, cmd: RecordTransactionCommand) -> RecordTransactionResponse:
        entries = [
            TransactionEntry(
                account_id=e.account_id,
                direction=EntryDirection(e.direction),
                amount=e.amount,
                currency=e.currency,
            )
            for e in cmd.entries
        ]

        tx = JournalTransaction(
            reference=cmd.reference,
            description=cmd.description,
            entries=entries,
        )

        # Load all affected accounts
        accounts: dict[str, Account] = {}
        for entry in entries:
            if entry.account_id not in accounts:
                acc = self.account_repo.get_by_id(entry.account_id)
                if acc is None:
                    raise AccountNotFoundError(f"Account '{entry.account_id}' not found.")
                accounts[entry.account_id] = acc

        # Apply entries
        for entry in entries:
            accounts[entry.account_id].apply_entry(entry)

        # Persist all
        for acc in accounts.values():
            self.account_repo.save(acc)
        self.ledger_repo.save_transaction(tx)

        return RecordTransactionResponse(
            transaction_id=tx.transaction_id,
            reference=tx.reference,
            entry_count=len(tx.entries),
        )


@query_handler(GetAccountBalanceQuery)
class GetAccountBalanceHandler:
    """Handler querying account balance."""

    def __init__(self, account_repo: AccountRepositoryPort) -> None:
        self.account_repo = account_repo

    def __call__(self, query: GetAccountBalanceQuery) -> GetAccountBalanceResponse:
        account = self.account_repo.get_by_id(query.account_id)
        if account is None:
            raise AccountNotFoundError(f"Account '{query.account_id}' not found.")

        return GetAccountBalanceResponse(
            account_id=account.account_id,
            currency=account.currency,
            balance=account.balance,
            status=account.status.value,
        )


@query_handler(ListLedgerEntriesQuery)
class ListLedgerEntriesHandler:
    """Handler listing ledger posting entries for an account."""

    def __init__(self, ledger_repo: LedgerRepositoryPort) -> None:
        self.ledger_repo = ledger_repo

    def __call__(self, query: ListLedgerEntriesQuery) -> ListLedgerEntriesResponse:
        entries = self.ledger_repo.get_entries_for_account(query.account_id)
        return ListLedgerEntriesResponse(
            account_id=query.account_id,
            entries=[
                PostingLineDto(
                    account_id=e.account_id,
                    direction=e.direction.value,
                    amount=e.amount,
                    currency=e.currency,
                )
                for e in entries
            ],
        )
