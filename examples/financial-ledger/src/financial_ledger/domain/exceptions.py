"""Domain exceptions for double-entry financial ledger."""

from __future__ import annotations

__all__ = [
    "AccountAlreadyExistsError",
    "AccountFrozenError",
    "AccountNotFoundError",
    "FinancialLedgerDomainError",
    "InsufficientFundsError",
    "InvalidAmountError",
    "UnbalancedTransactionError",
]


class FinancialLedgerDomainError(Exception):
    """Base exception for all financial ledger domain errors."""


class InsufficientFundsError(FinancialLedgerDomainError):
    """Raised when account balance is insufficient for debit."""


class UnbalancedTransactionError(FinancialLedgerDomainError):
    """Raised when sum of debits does not equal sum of credits."""


class AccountFrozenError(FinancialLedgerDomainError):
    """Raised when attempting to transact against a frozen or closed account."""


class AccountNotFoundError(FinancialLedgerDomainError):
    """Raised when an account is not found in the ledger."""


class AccountAlreadyExistsError(FinancialLedgerDomainError):
    """Raised when attempting to create an account with duplicate ID."""


class InvalidAmountError(FinancialLedgerDomainError):
    """Raised when transaction amount is non-positive or invalid."""
