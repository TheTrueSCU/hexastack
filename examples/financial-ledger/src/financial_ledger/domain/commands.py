"""CQRS commands and response DTOs for financial ledger."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from hexastack_core.domain import Command, Query
from pydantic import BaseModel, Field

__all__ = [
    "CreateAccountCommand",
    "CreateAccountResponse",
    "FreezeAccountCommand",
    "FreezeAccountResponse",
    "GetAccountBalanceQuery",
    "GetAccountBalanceResponse",
    "ListLedgerEntriesQuery",
    "ListLedgerEntriesResponse",
    "PostingLineDto",
    "RecordTransactionCommand",
    "RecordTransactionResponse",
    "TransferMoneyCommand",
    "TransferMoneyResponse",
]


class CreateAccountCommand(Command):
    """Command to create a new financial ledger account."""

    account_id: str | None = None
    tenant_id: str = "default"
    owner_id: str = "system"
    currency: str = "USD"
    initial_balance: Decimal = Field(default_factory=lambda: Decimal("0.00"))
    credit_limit: Decimal = Field(default_factory=lambda: Decimal("0.00"))


class CreateAccountResponse(BaseModel):
    """Response returned upon account creation."""

    account_id: str
    currency: str
    balance: Decimal
    status: str


class FreezeAccountCommand(Command):
    """Command to freeze an active account."""

    account_id: str
    reason: str = "Administrative freeze"


class FreezeAccountResponse(BaseModel):
    """Response returned upon freezing an account."""

    account_id: str
    status: str


class TransferMoneyCommand(Command):
    """Command to transfer funds between two accounts using double-entry posting."""

    source_account_id: str
    destination_account_id: str
    amount: Decimal
    reference: str
    description: str = "Account transfer"
    currency: str = "USD"


class TransferMoneyResponse(BaseModel):
    """Response returned upon successful transfer."""

    transaction_id: str
    reference: str
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    source_balance: Decimal
    destination_balance: Decimal


class PostingLineDto(BaseModel):
    """Posting line definition within a generic journal transaction."""

    account_id: str
    direction: str  # DEBIT or CREDIT
    amount: Decimal
    currency: str = "USD"


class RecordTransactionCommand(Command):
    """Command to record an arbitrary multi-legged balanced transaction."""

    reference: str
    description: str
    entries: list[PostingLineDto]


class RecordTransactionResponse(BaseModel):
    """Response returned upon recording a journal transaction."""

    transaction_id: str
    reference: str
    entry_count: int


class GetAccountBalanceQuery(Query):
    """Query to inspect an account balance and status."""

    account_id: str


class GetAccountBalanceResponse(BaseModel):
    """Response payload for account balance query."""

    account_id: str
    currency: str
    balance: Decimal
    status: str


class ListLedgerEntriesQuery(Query):
    """Query to list ledger transaction history for an account."""

    account_id: str


class ListLedgerEntriesResponse(BaseModel):
    """Response payload containing ledger transaction entries."""

    account_id: str
    entries: list[PostingLineDto]
