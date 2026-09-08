"""Abstract repository and ledger storage ports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from financial_ledger.domain.models import Account, JournalTransaction, TransactionEntry

__all__ = [
    "AccountRepositoryPort",
    "LedgerRepositoryPort",
]


class AccountRepositoryPort(ABC):
    """Abstract port for persisting and loading Account entities."""

    @abstractmethod
    def save(self, account: Account) -> None:
        """Persist an account state."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, account_id: str) -> Optional[Account]:
        """Retrieve an account by its unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Account]:
        """Retrieve all registered accounts."""
        raise NotImplementedError


class LedgerRepositoryPort(ABC):
    """Abstract port for persisting immutable journal transactions and entries."""

    @abstractmethod
    def save_transaction(self, transaction: JournalTransaction) -> None:
        """Persist a balanced double-entry journal transaction."""
        raise NotImplementedError

    @abstractmethod
    def get_transaction(self, transaction_id: str) -> Optional[JournalTransaction]:
        """Retrieve a transaction by identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_entries_for_account(self, account_id: str) -> list[TransactionEntry]:
        """Retrieve all historical posting lines for a specific account."""
        raise NotImplementedError
