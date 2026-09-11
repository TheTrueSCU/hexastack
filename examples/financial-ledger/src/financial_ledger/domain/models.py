"""Domain models and invariants for double-entry financial ledger.

Notes/Architectural Intent:
    Guarantees strict double-entry accounting invariants where every transaction consists
    of balanced debit and credit entries (sum(Debits) == sum(Credits)). All amounts use
    exact Decimal arithmetic to prevent floating-point inaccuracies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
import uuid

from financial_ledger.domain.exceptions import (
    AccountFrozenError,
    InsufficientFundsError,
    InvalidAmountError,
    UnbalancedTransactionError,
)

__all__ = [
    "Account",
    "AccountStatus",
    "EntryDirection",
    "JournalTransaction",
    "TransactionEntry",
]


class AccountStatus(StrEnum):
    """Lifecycle status of a financial account."""

    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class EntryDirection(StrEnum):
    """Direction of a ledger entry line (DEBIT or CREDIT)."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


@dataclass
class Account:
    """Financial account representing an asset, liability, equity, revenue, or expense.

    Notes/Architectural Intent:
        Accounts enforce status checks and balance invariants. Balance cannot drop below
        the allowed credit limit.
    """

    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = "default"
    owner_id: str = "system"
    currency: str = "USD"
    balance: Decimal = field(default_factory=lambda: Decimal("0.00"))
    credit_limit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def assert_active(self) -> None:
        """Verify that account is active and able to participate in transactions.

        Raises:
            AccountFrozenError: If account is not ACTIVE.
        """
        if self.status != AccountStatus.ACTIVE:
            raise AccountFrozenError(
                f"Account '{self.account_id}' is in status '{self.status}' and cannot transact."
            )

    def apply_entry(self, entry: TransactionEntry) -> None:
        """Apply a debit or credit entry to update account balance.

        Args:
            entry: Transaction entry line to apply.

        Raises:
            AccountFrozenError: If account is frozen or closed.
            InsufficientFundsError: If resulting balance breaches credit limit.
        """
        self.assert_active()
        if entry.direction == EntryDirection.CREDIT:
            self.balance += entry.amount
        elif entry.direction == EntryDirection.DEBIT:
            if (self.balance - entry.amount) < -self.credit_limit:
                raise InsufficientFundsError(
                    f"Insufficient funds on account '{self.account_id}'. Current: {self.balance}, Required: {entry.amount}"
                )
            self.balance -= entry.amount


@dataclass
class TransactionEntry:
    """Individual debit or credit posting line in a double-entry transaction."""

    account_id: str
    direction: EntryDirection
    amount: Decimal
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate entry amount is positive."""
        if self.amount <= Decimal("0.00"):
            raise InvalidAmountError(
                f"Entry amount must be strictly positive, got {self.amount}"
            )


@dataclass
class JournalTransaction:
    """Double-entry journal transaction composed of balanced debit and credit entries.

    Notes/Architectural Intent:
        The fundamental double-entry invariant requires sum(Debits) == sum(Credits).
        Transactions are immutable once constructed and validated.
    """

    reference: str
    description: str
    entries: list[TransactionEntry]
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate balanced double-entry invariant.

        Raises:
            UnbalancedTransactionError: If sum of debits != sum of credits.
        """
        if len(self.entries) < 2:
            raise UnbalancedTransactionError(
                "A double-entry transaction requires at least two posting lines."
            )

        total_debits = sum(
            (e.amount for e in self.entries if e.direction == EntryDirection.DEBIT),
            start=Decimal("0.00"),
        )
        total_credits = sum(
            (e.amount for e in self.entries if e.direction == EntryDirection.CREDIT),
            start=Decimal("0.00"),
        )

        if total_debits != total_credits:
            raise UnbalancedTransactionError(
                f"Unbalanced double-entry transaction '{self.reference}': "
                f"total debits ({total_debits}) != total credits ({total_credits})"
            )
